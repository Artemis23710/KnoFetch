import os
import base64
from datetime import datetime
import pandas as pd
import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings

from src.database import get_chromadb_collection
from src.search import hybrid_search
from src.llm import get_conversational_chain, generate_response_with_retry
from src.evaluation import evaluate_with_ragas, render_ragas_panel

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

    # Current question
    with st.container():
        with st.chat_message("user"):
            st.write(user_question)
        with st.chat_message("assistant"):
            st.write(response_output)
            st.info(source_info)

    # RAGAS evaluation
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
