class RAGPipeline:
    def __init__(self):
        self.documents = []
    
    def add_documents(self, docs):
        self.documents.extend(docs)
    
    def query(self, question):
        if not self.documents:
            return "No documents loaded."
        return f"Response based on {len(self.documents)} documents: {question}"

def create_vector_store(docs):
    return docs

def create_rag_chain(vector_store):
    return RAGPipeline()
