import os
import streamlit as st
import shutil
import asyncio
from langchain_huggingface import HuggingFaceEmbeddings

# Local imports
from src.config import load_dotenv
from src.chunking import create_parent_chunk_map
from src.pdf_utils import get_pdf_text_with_metadata, get_text_chunks_semantic
from src.database import store_chunks_in_chromadb
from src.ui_handlers import user_input

# Ensure an asyncio event loop exists in this thread context (required for ChromaDB/Streamlit on Windows)
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Load environment variables
load_dotenv()


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
    
    # Retrieve Groq API Key from environment (.env) first, fallback to session state
    env_api_key = os.getenv("GROQ_API_KEY", "")
    default_key = env_api_key if env_api_key else st.session_state.get('api_key', '')
    
    api_key = st.sidebar.text_input("Enter your Groq API Key:", value=default_key, type="password")
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
                shutil.rmtree("chroma_data")
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
            import pandas as pd
            import base64
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