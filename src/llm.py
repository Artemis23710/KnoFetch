import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, wait_random_exponential, stop_after_attempt

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
