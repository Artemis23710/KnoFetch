import os
import shutil
import asyncio
from typing import List, Optional
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, UploadFile, File, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_huggingface import HuggingFaceEmbeddings

# Local imports
from src.config import load_dotenv, get_groq_api_key
from src.chunking import create_parent_chunk_map
from src.pdf_utils import get_pdf_text_with_metadata, get_text_chunks_semantic
from src.database import store_chunks_in_chromadb, get_chromadb_collection
from src.search import hybrid_search
from src.llm import get_conversational_chain, generate_response_with_retry

# Load environment variables
load_dotenv()

app = FastAPI(title="Nexus RAG API Backend")

# CORS middleware to allow connection from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File-like wrapper to support .name attribute needed by get_pdf_text_with_metadata
class FileLikeWrapper:
    def __init__(self, filepath: str, filename: str):
        self.file = open(filepath, "rb")
        self.name = filename

    def read(self, *args, **kwargs):
        return self.file.read(*args, **kwargs)

    def seek(self, *args, **kwargs):
        return self.file.seek(*args, **kwargs)

    def tell(self, *args, **kwargs):
        return self.file.tell(*args, **kwargs)

    def close(self):
        self.file.close()

# RAG State cache manager
class RAGState:
    def __init__(self):
        self.all_documents = []
        self.parent_map = {}
        self.embeddings = None
        self.collection = None

    def initialize(self):
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            self.collection, _ = get_chromadb_collection()
            self.reload_cache()
        except Exception as e:
            print(f"Error initializing RAG state: {e}")

    def reload_cache(self):
        try:
            results = self.collection.get(include=['documents', 'metadatas'])
            if results and results['documents']:
                self.all_documents = results['documents']
                self.parent_map = {}
                for doc, meta in zip(results['documents'], results['metadatas']):
                    chunk_id = meta.get('chunk_id')
                    if chunk_id:
                        self.parent_map[chunk_id] = {
                            'full_content': doc,
                            'summary':      meta.get('summary', ''),
                            'page_number':  meta.get('page_number', 'Unknown'),
                            'doc_title':    meta.get('doc_title', 'Unknown'),
                            'doc_name':     meta.get('doc_name', 'Unknown')
                        }
                print(f"RAG Cache loaded: {len(self.all_documents)} chunks.")
            else:
                self.all_documents = []
                self.parent_map = {}
                print("RAG Cache is empty.")
        except Exception as e:
            print(f"Error reloading RAG cache: {e}")
            self.all_documents = []
            self.parent_map = {}

rag_state = RAGState()

@app.on_event("startup")
async def startup_event():
    rag_state.initialize()

@app.get("/api/health")
def health_check():
    return {"status": "ok", "documents_loaded": len(rag_state.all_documents)}

@app.get("/api/documents")
def get_documents():
    if not rag_state.parent_map:
        return []
    unique_docs = sorted(list(set(info['doc_name'] for info in rag_state.parent_map.values())))
    return unique_docs

class ChatRequest(BaseModel):
    question: str
    api_key: Optional[str] = None
    run_ragas: Optional[bool] = False

@app.post("/api/chat")
def chat(request: ChatRequest):
    api_key = request.api_key
    if api_key:
        api_key = api_key.strip()
        if api_key.lower() in ("null", "undefined", ""):
            api_key = None
            
    if not api_key:
        api_key = get_groq_api_key()

    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required. Please set GROQ_API_KEY or send it in the request.")

    if not rag_state.all_documents:
        raise HTTPException(status_code=400, detail="No documents uploaded. Please upload PDF files first.")

    try:
        search_results = hybrid_search(
            request.question,
            rag_state.collection,
            rag_state.embeddings,
            rag_state.all_documents,
            parent_map=rag_state.parent_map,
            k_vectors=15,
            k_keywords=15,
            k_final=8,
            api_key=api_key
        )

        if not search_results:
            return {
                "answer": "I couldn't find any relevant sections in the uploaded documents to answer your question.",
                "sources": [],
                "ragas": None
            }

        chain = get_conversational_chain("Groq Llama 3", api_key=api_key)
        if chain is None:
            raise HTTPException(status_code=500, detail="Failed to initialize the conversational chain.")

        docs_for_chain = [r['content'] for r in search_results]
        primary_metadata = search_results[0]

        response = generate_response_with_retry(
            chain, docs_for_chain, request.question, metadata=primary_metadata
        )
        answer = response.get('output_text', 'No response generated')

        sources = []
        for result in search_results:
            sources.append({
                "doc_name": result.get("doc_name", "Unknown"),
                "page_number": result.get("page_number", "Unknown"),
                "score": result.get("vector_score") if result.get("type") == "vector" else result.get("score"),
                "type": result.get("type", "hybrid"),
                "summary": result.get("summary", "")
            })

        # Run RAGAS evaluation if requested
        eval_result = None
        if request.run_ragas:
            from src.evaluation import evaluate_with_ragas
            eval_result = evaluate_with_ragas(
                request.question, answer, docs_for_chain, api_key
            )

        return {
            "answer": answer,
            "sources": sources,
            "ragas": eval_result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    temp_dir = os.path.join(os.getcwd(), "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    saved_paths = []
    wrappers = []
    try:
        for upload_file in files:
            file_path = os.path.join(temp_dir, upload_file.filename)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(upload_file.file, f)
            saved_paths.append(file_path)
            wrappers.append(FileLikeWrapper(file_path, upload_file.filename))

        # Process the PDFs using the wrapper objects (which have .name)
        pdf_data = get_pdf_text_with_metadata(wrappers)
        if not pdf_data:
            raise HTTPException(status_code=400, detail="No text could be extracted from the uploaded files.")

        chunks = get_text_chunks_semantic(pdf_data)
        if not chunks:
            raise HTTPException(status_code=400, detail="No semantic chunks could be created from the files.")

        # Store in database
        store_chunks_in_chromadb(chunks, rag_state.embeddings)
        
        # Reload cache
        rag_state.reload_cache()

        return {
            "message": f"Successfully processed {len(files)} files.",
            "chunks_created": len(chunks),
            "files": [f.filename for f in files]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing upload: {str(e)}")
    finally:
        # Close file handles and clean up temp files
        for w in wrappers:
            try:
                w.close()
            except Exception:
                pass
        for path in saved_paths:
            try:
                os.remove(path)
            except Exception:
                pass
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

@app.post("/api/reset")
def reset_database():
    try:
        collection, client = get_chromadb_collection()
        try:
            client.delete_collection("pdf_documents")
        except Exception:
            pass
        
        # Recreate collection to ensure it exists
        rag_state.collection = client.get_or_create_collection(
            name="pdf_documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Reset cache
        rag_state.all_documents = []
        rag_state.parent_map = {}
        
        # Try to delete chroma_data directory if possible
        if os.path.exists("chroma_data"):
            try:
                shutil.rmtree("chroma_data", ignore_errors=True)
            except Exception:
                pass
                
        return {"message": "Database and cache reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting database: {str(e)}")
