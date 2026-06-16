import re
import json
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

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
             '{{"score": <float 0.0-1.0>, "explanation": "<one sentence>"}}'),
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
             '{{"score": <float 0.0-1.0>, "explanation": "<one sentence>"}}'),
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
             '{{"score": <float 0.0-1.0>, "explanation": "<one sentence>"}}'),
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

