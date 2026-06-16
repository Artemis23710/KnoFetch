import chromadb
from chromadb.config import Settings

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
