class RAGPipeline:
    def __init__(self):
        self.documents = []
    
    def add_documents(self, docs):
        self.documents.extend(docs)
    
    def query(self, question):
        return f"Response to: {question}"
