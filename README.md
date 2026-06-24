# 📚 KnoFetch: Advanced RAG PDF Chatbot

**KnoFetch** is a production-grade, state-of-the-art Retrieval-Augmented Generation (RAG) application. It allows users to upload PDF documents, index them semantically into a local vector store, and ask questions through a high-performance chat interface. The system leverages hybrid search, query expansion, cross-encoder re-ranking, and **RAGAS (Retrieval Augmented Generation Assessment)** evaluations to deliver highly precise, hallucination-free, and verifiable answers.

---

## 🚀 Key Features

*   **PDF Indexing & Semantic Chunking**: Smartly splits uploaded PDF pages into semantic chunks based on sentence boundaries, preserving metadata like page numbers and document titles.
*   **Hybrid Search Engine**: Orchestrates dual retrieval combining vector similarity search (dense retrieval) and BM25 Okapi search (sparse keyword retrieval).
*   **Query Expansion**: Uses LLM-powered query expansion via Groq Llama 3 to generate search variations of the user's prompt, increasing context recall.
*   **Cross-Encoder Re-ranking**: Uses a pre-trained re-ranking model (`cross-encoder/mmarco-MiniLMv2-L12-H384-V1`) to re-score retrieved contexts, ensuring the most relevant passages are passed to the reader LLM.
*   **RAGAS Evaluation Panel**: Employs an LLM-as-a-judge mechanism to evaluate Faithfulness, Answer Relevance, and Context Precision after each response, outputting visual badges and detailed reasoning text.
*   **Downloadable History Logs**: Exporters to download the complete chat history logs and RAGAS scoring logs directly as CSV tables.
*   **Double Interface Compatibility**: Can be run as a modern **React SPA web application** (via Vite & FastAPI backend) or as a lightweight **Streamlit application**.

---

## 🛠️ Technologies & Libraries

### Frontend (SPA Web App)
*   **React** (v18) + **TypeScript**
*   **Vite** (Build system)
*   **Tailwind CSS** (Styling framework)
*   **Framer Motion** (Layout animations)
*   **Lucide Icons** (Iconography pack)

### Backend (API Server)
*   **FastAPI** & **Uvicorn** (Asynchronous ASGI server)
*   **ChromaDB** (Local persistent vector database)
*   **LangChain & LangChain Community** (LLM orchestration and prompt engineering)
*   **sentence-transformers** (All-MiniLM-L6-v2 embeddings)
*   **langchain-groq** (Groq cloud inference engine API)
*   **rank-bm25** (BM25 sparse retrieval)
*   **PyPDF2** (PDF text extraction)
*   **python-dotenv** (Environment variables loader)

---

## 📂 Project Structure

```text
KnoFetch/
├── src/                    # Core Python RAG implementation package
│   ├── chunking.py         # Text chunking and sentence boundary mapping
│   ├── config.py           # Environment variables configuration
│   ├── database.py         # ChromaDB indexing client management
│   ├── evaluation.py       # RAGAS metrics calculations
│   ├── llm.py              # LLM models initialization & retry loops
│   ├── pdf_utils.py        # PDF extraction helpers
│   ├── search.py           # Retrieval, expansion, and re-ranking logic
│   └── ui_handlers.py      # Streamlit-specific view renderers
├── Frontend/               # React SPA Frontend codebase
│   ├── src/
│   │   ├── components/     # UI elements (Sidebar, ChatInput, RagasPanel, etc.)
│   │   ├── lib/            # api.ts fetch endpoints integrations
│   │   ├── types/          # TypeScript structural interfaces
│   │   └── App.tsx         # Dashboard parent component
│   └── package.json
├── backend.py              # FastAPI ASGI Server running the API endpoints
├── app.py                  # Streamlit Server running the Streamlit app
├── .env                    # Key configurations (holds GROQ_API_KEY)
└── requirements.txt        # Python backend environment packages list
```

---

## ⚙️ Setup & Installation Instructions

Follow these steps to set up and run the application locally on your machine.

### Prerequisites
*   **Python** (v3.10 or v3.11 recommended)
*   **Node.js** (v18 or higher) and **npm**
*   A **Groq API Key** (Get a free key from the [Groq Console](https://console.groq.com/keys)).

---

### Step 1: Backend Setup
1.  Navigate to the project root directory:
    ```bash
    cd KnoFetch
    ```
2.  Create a Python virtual environment:
    ```bash
    python -m venv env
    ```
3.  Activate the virtual environment:
    *   **Windows (PowerShell)**:
        ```powershell
        .\env\Scripts\Activate.ps1
        ```
    *   **Mac/Linux**:
        ```bash
        source env/bin/activate
        ```
4.  Install the required Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
5.  Create a `.env` file in the root folder and add your Groq API key:
    ```env
    GROQ_API_KEY=your_groq_api_key_here
    ```

---

### Step 2: Frontend Setup
1.  Navigate to the `Frontend` directory:
    ```bash
    cd Frontend
    ```
2.  Install the frontend node modules:
    ```bash
    npm install
    ```

---

## 🏃 Running the Application

### Option A: Run the React + FastAPI Stack (Recommended)
This launches the modern Web SPA.

1.  **Start the FastAPI Backend**:
    From the root directory (`KnoFetch`), with your virtual environment activated:
    ```bash
    python -m uvicorn backend:app --reload
    ```
    *The API server will run on `http://localhost:8000`.*

2.  **Start the React Frontend**:
    Open a new terminal window, navigate to the `Frontend` directory:
    ```bash
    cd Frontend
    npm run dev
    ```
    *The React app will run on `http://localhost:5173`. Open your browser and navigate here to use KnoFetch!*

---

### Option B: Run the Streamlit Application
This launches the single-page Streamlit dashboard.

1.  From the root directory (`KnoFetch`), with your virtual environment activated, run:
    ```bash
    streamlit run app.py
    ```
    *The Streamlit dashboard will open in your browser automatically.*

---

## 💡 How to Use KnoFetch

1.  **Upload Documents**: In the React sidebar, drag/click under **Submit & Process PDF** to select one or more PDF files. The backend will parse, chunk, embed, and store them.
2.  **Verify Indexing**: Once processing is complete, you will see the filenames appear in the **Documents** list of your sidebar. A success status message will also appear in the chat panel.
3.  **Toggle RAGAS (Optional)**: Check the **Enable RAGAS evaluation** box in the sidebar if you wish to run judge metrics on answers.
4.  **Ask Questions**: Type your prompt into the input bar. The chatbot will retrieve semantic contexts, expand your query, query Llama 3 via Groq, and return a cited answer.
5.  **Examine Citations**: Cited files and page numbers are displayed at the bottom of the response block under **Sources**.
6.  **Reset Store**: To delete your document indexes and start fresh, click the **Clear DB** link in the sidebar next to the Documents header.
