
import streamlit as st
from rag_pipeline import create_vector_store, create_rag_chain

st.set_page_config(page_title="Baby AI", page_icon="🤖", layout="wide")
st.title("👶 Baby AI - Your Smart Assistant")
st.write("Upload documents and ask Baby AI anything!")

# Upload documents
uploaded_files = st.file_uploader("Upload text files", accept_multiple_files=True)
docs = []
if uploaded_files:
    for file in uploaded_files:
        docs.append(file.read().decode("utf-8"))

if docs:
    st.success("Documents uploaded successfully!")
    vector_store = create_vector_store(docs)
    rag_chain = create_rag_chain(vector_store)

    # Ask questions
    query = st.text_input("Ask Baby AI a question:")
    if st.button("Get Answer"):
        if query:
            answer = rag_chain.run(query)
            st.markdown(f"**Answer:** {answer}")
