import streamlit as st
from rag_pipeline import RAGPipeline

st.title("RAG Application")

if "rag" not in st.session_state:
    st.session_state.rag = RAGPipeline()

query = st.text_input("Enter your question:")

if st.button("Search") and query:
    with st.spinner("Processing..."):
        result = st.session_state.rag.query(query)
        st.write(result)
