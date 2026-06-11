import os
import streamlit as st
import pandas as pd
import base64
import re
import json
import numpy

# LangChain imports
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

# Core imports
from datetime import datetime
import asyncio
from PyPDF2 import PdfReader
from tenacity import retry, wait_random_exponential, stop_after_attempt

# Advanced Search imports
import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())


# ============================================================================
# SEMANTIC CHUNKING
# ============================================================================

def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def semantic_chunk(text, target_size=800, overlap_size=150):
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        sentences = split_into_sentences(paragraph)
        for sentence in sentences:
            test_chunk = (current_chunk + " " + sentence).strip()
            if len(test_chunk) > target_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk = test_chunk
        if current_chunk:
            current_chunk += "\n"
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks


# ============================================================================
# QUERY EXPANSION
# ============================================================================

def expand_query(query, llm_model, api_key):
    try:
        model = ChatGroq(
            temperature=0.1,
            groq_api_key=api_key,
            model_name="llama-3.1-8b-instant"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a query expansion expert. Create 3 alternative versions of the "
             "user's query that capture the same intent but use different terminology.\n\n"
             "Output ONLY valid JSON, no markdown:\n"
             '{"queries": ["query1", "query2", "query3"]}'),
            ("human", f"Original query: {query}")
        ])
        chain = prompt | model
        response = chain.invoke({"query": query})
        try:
            response_text = response.content if hasattr(response, 'content') else str(response)
            expanded = json.loads(response_text)
            return ([query] + expanded.get('queries', [])[:2])[:3]
        except Exception:
            return [query]
    except Exception:
        return [query]


# ============================================================================
# BM25 KEYWORD SEARCH
# ============================================================================

@st.cache_resource
def get_bm25_index(documents):
    tokenized_docs = [doc.lower().split() for doc in documents]
    bm25 = BM25Okapi(tokenized_docs)
    return bm25, documents


def keyword_search_bm25(query, all_documents, k=5):
    try:
        bm25, docs = get_bm25_index(all_documents)
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [
            {'content': docs[idx], 'score': float(scores[idx]), 'type': 'keyword'}
            for idx in top_indices if scores[idx] > 0
        ]
    except Exception:
        return []


# ============================================================================
# RE-RANKING
# ============================================================================

@st.cache_resource
def load_reranker():
    try:
        return CrossEncoder('cross-encoder/mmarco-MiniLMv2-L12-H384-V1')
    except Exception:
        return None


def rerank_results(query, candidates, reranker, top_k=5):
    if not reranker or not candidates:
        return candidates[:top_k]
    try:
        pairs = [[query, cand['content'][:512]] for cand in candidates]
        scores = reranker.predict(pairs)
        for i, candidate in enumerate(candidates):
            candidate['rerank_score'] = float(scores[i])
        return sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)[:top_k]
    except Exception:
        return candidates[:top_k]


# ============================================================================
# SMALL-TO-BIG RETRIEVAL
# ============================================================================

def create_parent_chunk_map(chunks_with_metadata):
    return {
        chunk['chunk_id']: {
            'full_content': chunk['content'],
            'summary':      chunk['summary'],
            'page_number':  chunk['page_number'],
            'doc_title':    chunk['doc_title'],
            'doc_name':     chunk['doc_name']
        }
        for chunk in chunks_with_metadata
    }


def expand_chunk_with_context(chunk_id, parent_map):
    if chunk_id not in parent_map:
        return None
    return parent_map[chunk_id]['full_content']


# ============================================================================
# HYBRID SEARCH
# ============================================================================

def hybrid_search(query, collection, embedding_model, all_documents,
                  parent_map=None, k_vectors=10, k_keywords=10, k_final=5):
    expanded_queries = expand_query(query, "groq", st.session_state.get('api_key', ''))
    all_candidates = []

    for expanded_query in expanded_queries:
        try:
            query_embedding = embedding_model.embed_query(expanded_query)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=k_vectors,
                include=['documents', 'metadatas', 'distances']
            )
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    all_candidates.append({
                        'content':      doc,
                        'page_number':  metadata.get('page_number', 'Unknown'),
                        'doc_title':    metadata.get('doc_title', 'Unknown'),
                        'doc_name':     metadata.get('doc_name', 'Unknown'),
                        'summary':      metadata.get('summary', ''),
                        'chunk_id':     metadata.get('chunk_id', ''),
                        'vector_score': 1.0 - results['distances'][0][i],
                        'type':         'vector'
                    })
        except Exception:
            pass

    all_candidates.extend(keyword_search_bm25(query, all_documents, k=k_keywords))

    unique_candidates = {}
    for c in all_candidates:
        key = c['content'][:100]
        if key not in unique_candidates:
            unique_candidates[key] = c
    candidates = list(unique_candidates.values())

    reranker = load_reranker()
    if reranker:
        candidates = rerank_results(query, candidates, reranker, top_k=k_final)
    else:
        candidates = sorted(candidates, key=lambda x: x.get('vector_score', 0), reverse=True)[:k_final]

    final_results = []
    for candidate in candidates:
        if parent_map and candidate.get('chunk_id') in parent_map:
            expanded = expand_chunk_with_context(candidate['chunk_id'], parent_map)
            if expanded:
                candidate['content'] = expanded
        final_results.append(candidate)

    return final_results


# ============================================================================
# RAGAS EVALUATION
# ============================================================================

def evaluate_with_ragas(question: str, answer: str, contexts: list, api_key: str) -> dict:
    """LLM-as-judge RAGAS metrics via Groq (no OpenAI key needed)."""
    try:
        llm = ChatGroq(
            temperature=0.0,
            groq_api_key=api_key,
            model_name="llama-3.1-8b-instant"
        )
        context_text = "\n\n---\n\n".join(str(c) for c in contexts[:3])

        def call_and_parse(prompt_template):
            try:
                chain = prompt_template | llm
                response = chain.invoke({})
                text = response.content if hasattr(response, 'content') else str(response)
                text = re.sub(r'```(?:json)?', '', text).strip().strip('`').strip()
                data = json.loads(text)
                score = max(0.0, min(1.0, float(data.get('score', 0.5))))
                return score, data.get('explanation', 'No explanation provided.')
            except Exception as e:
                return 0.5, f"Could not parse score: {e}"

        faith_prompt = ChatPromptTemplate.from_messages([
            ("system",
            "You are an expert evaluator measuring FAITHFULNESS of an AI answer.\n\n"
            "Faithfulness: every factual claim in the answer must be directly supported "
            "by the provided context. Facts NOT in the context lower the score.\n\n"
            "Score 0.0 (completely hallucinated) to 1.0 (every claim is in the context).\n\n"
            "Return ONLY valid JSON, no extra text:\n"
            '{{"score": <float 0.0-1.0>, "explanation": "<one sentence>"}}'),  # << doubled braces
            ("human",
            f"Context:\n{context_text}\n\nAnswer:\n{answer}\n\n"
            "Rate the faithfulness of the answer to the context.")
        ])

        rel_prompt = ChatPromptTemplate.from_messages([
            ("system",
            "You are an expert evaluator measuring ANSWER RELEVANCE.\n\n"
            "Answer relevance: the answer directly and completely addresses what was asked.\n\n"
            "Score 0.0 (completely irrelevant) to 1.0 (perfectly on-topic).\n\n"
            "Return ONLY valid JSON, no extra text:\n"
            '{{"score": <float 0.0-1.0>, "explanation": "<one sentence>"}}'),  # << doubled braces
            ("human",
            f"Question:\n{question}\n\nAnswer:\n{answer}\n\n"
            "Rate how well the answer addresses the question.")
        ])

        prec_prompt = ChatPromptTemplate.from_messages([
            ("system",
            "You are an expert evaluator measuring CONTEXT PRECISION.\n\n"
            "Context precision: the retrieved chunks contain information actually useful "
            "to answer the question. Irrelevant chunks lower this score.\n\n"
            "Score 0.0 (context completely irrelevant) to 1.0 (context perfectly covers the answer).\n\n"
            "Return ONLY valid JSON, no extra text:\n"
            '{{"score": <float 0.0-1.0>, "explanation": "<one sentence>"}}'),  # << doubled braces
            ("human",
            f"Question:\n{question}\n\nRetrieved Context:\n{context_text}\n\n"
            "Rate how well the context supports answering the question.")
        ])

        faith_score, faith_reason = call_and_parse(faith_prompt)
        rel_score,   rel_reason   = call_and_parse(rel_prompt)
        prec_score,  prec_reason  = call_and_parse(prec_prompt)
        overall = round((faith_score + rel_score + prec_score) / 3, 3)

        return {
            "faithfulness":      round(faith_score, 3),
            "answer_relevance":  round(rel_score,   3),
            "context_precision": round(prec_score,  3),
            "overall_score":     overall,
            "details": {
                "faithfulness_reason":      faith_reason,
                "answer_relevance_reason":  rel_reason,
                "context_precision_reason": prec_reason,
            }
        }
    except Exception as e:
        return {"error": str(e)}


def render_ragas_panel(eval_result: dict):
    if "error" in eval_result:
        st.error(f"RAGAS evaluation failed: {eval_result['error']}")
        return

    def badge(s):
        return "🟢" if s >= 0.75 else ("🟡" if s >= 0.50 else "🔴")

    def label(s):
        return "Good" if s >= 0.75 else ("Moderate" if s >= 0.50 else "Poor")

    faith   = eval_result["faithfulness"]
    rel     = eval_result["answer_relevance"]
    prec    = eval_result["context_precision"]
    overall = eval_result["overall_score"]
    details = eval_result.get("details", {})

    st.markdown("---")
    st.markdown("### 📊 RAGAS Evaluation")
    st.caption("LLM-as-judge scores — higher is better (0 = worst, 1 = best)")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"{badge(faith)} Faithfulness",     f"{faith:.2f}",
                help="1.0 = no hallucination.")
    col2.metric(f"{badge(rel)} Answer Relevance",   f"{rel:.2f}",
                help="1.0 = perfectly on-topic.")
    col3.metric(f"{badge(prec)} Context Precision", f"{prec:.2f}",
                help="1.0 = retrieval found the right chunks.")
    col4.metric(f"{badge(overall)} Overall",         f"{overall:.2f}",
                help="Average of the three metrics.")

    with st.expander("🔍 Detailed explanations", expanded=False):
        st.markdown(f"**Faithfulness** ({label(faith)}): {details.get('faithfulness_reason','N/A')}")
        st.markdown(f"**Answer Relevance** ({label(rel)}): {details.get('answer_relevance_reason','N/A')}")
        st.markdown(f"**Context Precision** ({label(prec)}): {details.get('context_precision_reason','N/A')}")

    if faith < 0.5:
        st.warning("⚠️ **Low Faithfulness** — the answer may contain hallucinations.")
    if rel < 0.5:
        st.warning("⚠️ **Low Answer Relevance** — the answer may not address the question.")
    if prec < 0.5:
        st.warning("⚠️ **Low Context Precision** — retrieval may be returning wrong chunks.")


# ============================================================================
# PDF PROCESSING
# ============================================================================

def get_pdf_text_with_metadata(pdf_docs):
    pdf_data = []
    for pdf in pdf_docs:
        doc_title = pdf.name.replace('.pdf', '')
        pdf_reader = PdfReader(pdf)
        for page_num, page in enumerate(pdf_reader.pages, 1):
            text = page.extract_text()
            if text and text.strip():
                pdf_data.append({
                    'text':        text,
                    'doc_title':   doc_title,
                    'page_number': page_num,
                    'doc_name':    pdf.name
                })
    return pdf_data


def get_text_chunks_semantic(pdf_data, model_name=None):
    chunks_with_metadata = []
    for item in pdf_data:
        chunks = semantic_chunk(item['text'], target_size=800, overlap_size=150)
        for chunk_idx, chunk in enumerate(chunks):
            if chunk.strip():
                summary = chunk[:150] + "..." if len(chunk) > 150 else chunk
                chunks_with_metadata.append({
                    'content':     chunk,
                    'doc_title':   item['doc_title'],
                    'page_number': item['page_number'],
                    'doc_name':    item['doc_name'],
                    'summary':     summary,
                    'chunk_id':    f"{item['doc_title']}_p{item['page_number']}_c{chunk_idx}"
                })
    return chunks_with_metadata


def get_chromadb_collection(collection_name="pdf_documents"):
    client = chromadb.PersistentClient(
        path="./chroma_data",
        settings=Settings(anonymized_telemetry=False)
    )
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    return collection, client


def store_chunks_in_chromadb(chunks_with_metadata, embedding_model):
    collection, client = get_chromadb_collection()
    embeddings_list = embedding_model.embed_documents(
        [chunk['content'] for chunk in chunks_with_metadata]
    )
    ids, embeddings, documents, metadatas = [], [], [], []
    for i, chunk in enumerate(chunks_with_metadata):
        ids.append(chunk['chunk_id'])
        embeddings.append(embeddings_list[i])
        documents.append(chunk['content'])
        metadatas.append({
            'page_number': str(chunk['page_number']),
            'doc_title':   chunk['doc_title'],
            'doc_name':    chunk['doc_name'],
            'summary':     chunk['summary'],
            'chunk_id':    chunk['chunk_id']
        })
    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    return collection, client


# ============================================================================
# LLM CHAIN
# ============================================================================

def get_conversational_chain(model_name, api_key=None):
    if model_name != "Groq Llama 3":
        st.error(f"Model '{model_name}' is not supported.")
        return None
    return ChatGroq(
        temperature=0.3,
        groq_api_key=api_key,
        model_name="llama-3.1-8b-instant"
    )


@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(3))
def generate_response_with_retry(chain, docs, user_question, metadata=None):
    doc_title   = metadata.get('doc_title',   'Unknown') if metadata else 'Unknown'
    page_number = metadata.get('page_number', 'Unknown') if metadata else 'Unknown'
    summary     = metadata.get('summary',     '')        if metadata else ''

    context = "\n\n---\n\n".join(
        doc['content'] if isinstance(doc, dict) else doc for doc in docs
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a precise document assistant. Answer ONLY using facts explicitly "
         "stated in the provided context below. Follow these strict rules:\n\n"
         "1. NEVER add facts from outside the context, even if you know them.\n"
         "2. If the context contains the answer, give it directly and concisely.\n"
         "3. If the question asks for a number or specific fact, lead with that.\n"
         "4. If PART of the question is not covered by the context, explicitly say "
         "   'The context does not contain information about [missing part]' "
         "   rather than filling the gap from your own knowledge.\n"
         "5. Do NOT speculate, infer, or use facts from your training data.\n"
         "6. Structure your answer by what the context actually says — "
         "   do not add sections for topics the context doesn't cover.\n\n"
         f"Context:\n{context}\n\n"
         f"Source: {doc_title} | Page: {page_number}"),
        ("human", "{question}")
    ])

    response = (prompt | chain).invoke({"question": user_question})
    answer   = response.content if hasattr(response, 'content') else str(response)
    return {"output_text": answer}


# ============================================================================
# USER INTERACTION
# ============================================================================

_CHAT_CSS = """
<style>
.chat-message {padding:1.5rem;border-radius:.5rem;margin-bottom:1rem;display:flex;}
.chat-message.user {background-color:#2b313e;}
.chat-message.bot  {background-color:#475063;}
.chat-message .avatar {width:20%;}
.chat-message .avatar img {max-width:78px;max-height:78px;border-radius:50%;object-fit:cover;}
.chat-message .message {width:80%;padding:0 1.5rem;color:#fff;}
.source-info {background-color:#1f3a5f;border-left:4px solid #00d4ff;padding:1rem;
              margin-top:.5rem;border-radius:.25rem;font-size:.85rem;color:#e0e0e0;}
</style>
"""

def _chat_bubble(question, answer, source_info=""):
    return f"""
    <div class="chat-message user">
        <div class="avatar"><img src="https://i.ibb.co/CKpTnWr/user-icon-2048x2048-ihoxz4vq.png"></div>
        <div class="message">{question}</div>
    </div>
    <div class="chat-message bot">
        <div class="avatar"><img src="https://i.ibb.co/wNmYHsx/langchain-logo.webp"></div>
        <div class="message">{answer}<div class="source-info">{source_info}</div></div>
    </div>"""


def user_input(user_question, model_name, api_key, pdf_docs, conversation_history,
               all_documents=None, parent_map=None, run_ragas=False):
    if not api_key:
        st.warning("Please provide a Groq API key first.")
        return
    if not os.path.exists("chroma_data"):
        st.warning("Please upload PDFs, click 'Submit & Process', and provide an API key first.")
        return

    response_output    = ""
    source_info        = ""
    source_doc         = "Unknown"
    page_num           = "Unknown"
    retrieved_contexts = []

    if model_name == "Groq Llama 3":
        try:
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            collection, _ = get_chromadb_collection()

            with st.spinner("🔍 Performing hybrid search with re-ranking..."):
                search_results = hybrid_search(
                        user_question, collection, embeddings,
                        all_documents or [],
                        parent_map=parent_map,
                        k_vectors=15,  
                        k_keywords=15, 
                        k_final=8   
                    )

            if not search_results:
                st.error("No relevant documents found.")
                return

            chain = get_conversational_chain("Groq Llama 3", api_key=api_key)
            if chain is None:
                return

            docs_for_chain     = [r['content'] for r in search_results]
            retrieved_contexts = docs_for_chain
            primary_metadata   = search_results[0]

            response        = generate_response_with_retry(chain, docs_for_chain, user_question, metadata=primary_metadata)
            response_output = response.get('output_text', 'No response generated')
            source_doc      = primary_metadata.get('doc_name', 'Unknown')
            page_num        = primary_metadata.get('page_number', 'Unknown')
            source_info     = f"Sources: {source_doc} | Page: {page_num}"

            search_method = primary_metadata.get('type', 'hybrid')
            if search_method == 'vector':
                source_info += f" | Relevance: {primary_metadata.get('vector_score',0)*100:.1f}% (Vector)"
            elif search_method == 'keyword':
                source_info += f" | Relevance: {primary_metadata.get('score',0):.2f} (Keyword)"

            pdf_names = [pdf.name for pdf in pdf_docs] if pdf_docs else []
            conversation_history.append((
                user_question, response_output, model_name,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ", ".join(pdf_names), source_doc, page_num
            ))

        except Exception as e:
            st.error(f"Error processing question: {e}")
            return

    # Replace the st.markdown(_CHAT_CSS + _chat_bubble(...)) call with this:

    # Current question
    with st.container():
        with st.chat_message("user"):
            st.write(user_question)
        with st.chat_message("assistant"):
            st.write(response_output)
            st.info(source_info)

    # RAGAS evaluation (keep as-is, it already uses st components)
    if run_ragas and retrieved_contexts and response_output:
        with st.spinner("📊 Running RAGAS evaluation (3 LLM-as-judge calls)..."):
            eval_result = evaluate_with_ragas(user_question, response_output, retrieved_contexts, api_key)
        render_ragas_panel(eval_result)

        if 'ragas_history' not in st.session_state:
            st.session_state.ragas_history = []
        st.session_state.ragas_history.append({
            "question": user_question,
            "eval": {k: v for k, v in eval_result.items() if k != 'details'}
        })

    # Older history
    history_to_show = conversation_history[:-1] if conversation_history else []
    for q, a, _, _, _, src, pg in reversed(history_to_show):
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            st.write(a)
            st.caption(f"Source: {src} | Page: {pg}")

    # CSV export
    if st.session_state.conversation_history:
        df  = pd.DataFrame(st.session_state.conversation_history,
                           columns=["Question","Answer","Model","Timestamp",
                                    "PDF Names","Source Document","Page Number"])
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        st.sidebar.markdown(
            f'<a href="data:file/csv;base64,{b64}" download="conversation_history.csv">'
            f'<button>📥 Download conversation history</button></a>',
            unsafe_allow_html=True
        )

    st.snow()


# ============================================================================
# MAIN
# ============================================================================

def main():
    st.set_page_config(page_title="Advanced RAG (v5)", page_icon=":books:")
    st.header("Advanced RAG · Hybrid Search · RAGAS Evaluation (v5) :books:")
    st.markdown("*Semantic Chunking · ChromaDB · Hybrid Search · Re-ranking · Query Expansion · **RAGAS***")

    for key, default in [
        ('conversation_history', []),
        ('all_documents', []),
        ('parent_map', {}),
        ('ragas_history', []),
        ('api_key', None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    st.sidebar.markdown(
        "[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/snsupratim/) "
        "[![Kaggle](https://img.shields.io/badge/Kaggle-20BEFF?style=for-the-badge&logo=kaggle&logoColor=white)](https://www.kaggle.com/snsupratim/) "
        "[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/snsupratim/)"
    )

    model_name = st.sidebar.radio("Select the Model:", ("Groq Llama 3",))
    api_key    = st.sidebar.text_input("Enter your Groq API Key:", type="password")
    st.session_state.api_key = api_key
    st.sidebar.markdown("Click [here](https://console.groq.com/keys) to get a free API key.")
    if not api_key:
        st.sidebar.warning("Please enter your Groq API Key to proceed.")
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 RAGAS Evaluation")
    run_ragas = st.sidebar.toggle(
        "Enable RAGAS after each answer", value=False,
        help="3 extra Groq calls per question to score Faithfulness, Answer Relevance, Context Precision."
    )
    if run_ragas:
        st.sidebar.info("⚡ RAGAS ON — ~4 API calls per question.")

    with st.sidebar:
        st.title("Menu:")
        col1, col2 = st.columns(2)
        reset_button = col2.button("Reset")
        clear_button = col1.button("Rerun")

        if reset_button:
            for k in ['conversation_history','all_documents','parent_map','ragas_history']:
                st.session_state[k] = [] if k != 'parent_map' else {}
            if os.path.exists("chroma_data"):
                import shutil; shutil.rmtree("chroma_data")
            st.success("✅ All data cleared!")
            st.rerun()
        elif clear_button:
            st.session_state.user_question = ""
            if st.session_state.conversation_history:
                st.session_state.conversation_history.pop()
            st.warning("Previous query discarded.")

        pdf_docs = st.file_uploader(
            "Upload PDF Files then click Submit & Process",
            accept_multiple_files=True
        )

        if st.button("Submit & Process"):
            if not pdf_docs:
                st.warning("Please upload PDF files first.")
            else:
                with st.spinner("Processing PDFs..."):
                    try:
                        pdf_data = get_pdf_text_with_metadata(pdf_docs)
                        if not pdf_data:
                            st.error("No text extracted. Check your files.")
                            return
                        chunks = get_text_chunks_semantic(pdf_data)
                        if not chunks:
                            st.error("No chunks created. Check your files.")
                            return
                        embeddings = HuggingFaceEmbeddings(
                            model_name="sentence-transformers/all-MiniLM-L6-v2"
                        )
                        store_chunks_in_chromadb(chunks, embeddings)
                        st.session_state.all_documents = [c['content'] for c in chunks]
                        st.session_state.parent_map    = create_parent_chunk_map(chunks)
                        st.success(f"✅ Processed {len(chunks)} semantic chunks!")
                        st.info(
                            "**Features active:** Semantic Chunking · Hybrid Search · "
                            "Query Expansion · Re-ranking · Small-to-Big · RAGAS (toggle sidebar)"
                        )
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

        # RAGAS CSV export
        if st.session_state.ragas_history:
            ragas_df = pd.DataFrame([
                {"Question": r["question"],
                 "Faithfulness":      r["eval"].get("faithfulness", ""),
                 "Answer Relevance":  r["eval"].get("answer_relevance", ""),
                 "Context Precision": r["eval"].get("context_precision", ""),
                 "Overall Score":     r["eval"].get("overall_score", "")}
                for r in st.session_state.ragas_history
            ])
            csv_r = ragas_df.to_csv(index=False)
            b64_r = base64.b64encode(csv_r.encode()).decode()
            st.sidebar.markdown(
                f'<a href="data:file/csv;base64,{b64_r}" download="ragas_scores.csv">'
                f'<button>📥 Download RAGAS scores</button></a>',
                unsafe_allow_html=True
            )

    user_question = st.text_input("Ask a Question from the PDF Files")
    if user_question:
        user_input(
            user_question, model_name, api_key, pdf_docs,
            st.session_state.conversation_history,
            all_documents=st.session_state.all_documents,
            parent_map=st.session_state.parent_map,
            run_ragas=run_ragas
        )
        st.session_state.user_question = ""


if __name__ == "__main__":
    main()