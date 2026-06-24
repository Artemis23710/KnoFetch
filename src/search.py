import json
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from src.chunking import expand_chunk_with_context
from src.config import get_groq_api_key

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


def hybrid_search(query, collection, embedding_model, all_documents,
                  parent_map=None, k_vectors=10, k_keywords=10, k_final=5, api_key=None):
    if api_key is None:
        try:
            api_key = st.session_state.get('api_key', '')
        except Exception:
            api_key = get_groq_api_key()
    expanded_queries = expand_query(query, "groq", api_key)
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
