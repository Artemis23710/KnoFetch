# KnoFetch
# Refactoring Walkthrough & Env Configuration

We have successfully refactored the codebase to be modular and cleaner. We also added support for a `.env` file to load the Groq API key automatically.

## Changes Made

### 1. Added `.env` Support
- Created [.env](file:///c:/Projects/KnoFetch/.env) and [.env.example](file:///c:/Projects/KnoFetch/.env.example) to host the `GROQ_API_KEY`.
- Modified [requirements.txt](file:///c:/Projects/KnoFetch/requirements.txt) to include `python-dotenv`.
- Created [src/config.py](file:///c:/Projects/KnoFetch/src/config.py) to load `.env` variables at runtime.

### 2. Code Refactoring (Splitting app.py)
Created a clean Python package structure inside the `src/` directory:
- [src/__init__.py](file:///c:/Projects/KnoFetch/src/__init__.py): Package initialization.
- [src/chunking.py](file:///c:/Projects/KnoFetch/src/chunking.py): Text preprocessing, sentence splitting, semantic chunking, and parent mapping.
- [src/pdf_utils.py](file:///c:/Projects/KnoFetch/src/pdf_utils.py): PDF parsing and text/chunk extraction logic.
- [src/database.py](file:///c:/Projects/KnoFetch/src/database.py): ChromaDB client management and chunk indexing.
- [src/search.py](file:///c:/Projects/KnoFetch/src/search.py): BM25 keyword search, query expansion, reranking models, and hybrid search orchestration.
- [src/llm.py](file:///c:/Projects/KnoFetch/src/llm.py): Conversation chains creation and retry wrappers.
- [src/evaluation.py](file:///c:/Projects/KnoFetch/src/evaluation.py): RAGAS metrics computation and UI rendering.
- [src/ui_handlers.py](file:///c:/Projects/KnoFetch/src/ui_handlers.py): Streamlit chat views, styling, user inputs processing, and data downloads.

### 3. Main Script Update
- Modified [app.py](file:///c:/Projects/KnoFetch/app.py) to remove monolithic helper functions, import them from the `src/` package instead, load environment variables using `python-dotenv`, and pre-populate the Groq API key field in the Streamlit sidebar automatically if configured.

## Verification
- Ran python import checks on the refactored script.
- Output: `app.py imports successfully!`

