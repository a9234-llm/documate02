"""Minimal Streamlit UI for asking questions to the RAG assistant."""
from __future__ import annotations

import streamlit as st
import time

from src.llm.rag_chain import answer_question
from src.app import db


def main():
    st.set_page_config(page_title="DocuMate RAG", layout="wide")
    st.title("DocuMate — RAG assistant for FastAPI docs")

    query = st.text_input("Enter your question about FastAPI docs:")
    prompt_variant = st.selectbox("Prompt variant", ["expert_role", "baseline", "structured"], index=0)
    col1, col2 = st.columns([3, 1])

    with col1:
        if st.button("Ask") and query.strip():
            start = time.time()
            with st.spinner("Retrieving and generating answer..."):
                out = answer_question(query, prompt_variant=prompt_variant, top_k=5)
            elapsed = int((time.time() - start) * 1000)
            answer = out.get("answer") or "(no answer)"
            sources = out.get("sources", [])

            st.markdown("**Answer:**")
            st.write(answer)

            st.markdown("**Sources:**")
            for s in sources:
                url = s.get("url") or ""
                label = f"{s.get('source_file') or ''} — {s.get('heading') or ''}"
                if url:
                    st.markdown(f"- [{label}]({url})")
                else:
                    st.markdown(f"- {label}")

            # log interaction
            try:
                interaction_id = db.log_interaction(query, answer, retrieval_method="dense", prompt_variant=prompt_variant, response_time_ms=elapsed, sources=sources)
                st.session_state.setdefault("last_interaction_id", interaction_id)
            except Exception as e:
                st.warning(f"Failed to log interaction: {e}")

    with col2:
        st.markdown("### Feedback")
        if st.button("👍 Upvote"):
            iid = st.session_state.get("last_interaction_id")
            if iid:
                db.update_feedback(iid, 1)
                st.success("Thanks for the feedback!")
            else:
                st.info("Ask a question first to send feedback.")
        if st.button("👎 Downvote"):
            iid = st.session_state.get("last_interaction_id")
            if iid:
                db.update_feedback(iid, -1)
                st.success("Thanks for the feedback!")
            else:
                st.info("Ask a question first to send feedback.")


if __name__ == "__main__":
    main()
