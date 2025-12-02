
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.llms import HuggingFacePipeline
from langchain.chains import RetrievalQA
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# Load embeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def create_vector_store(docs):
    """Create FAISS vector store from documents"""
    return FAISS.from_texts(docs, embeddings)

def load_llm():
    """Load open-source LLM"""
    model_name = "mistralai/Mistral-7B-Instruct-v0.1"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_length=512)
    return HuggingFacePipeline(pipeline=pipe)

def create_rag_chain(vector_store):
    """Create RAG chain with retriever and LLM"""
    retriever = vector_store.as_retriever()
    llm = load_llm()
    return RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
