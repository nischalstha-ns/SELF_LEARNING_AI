class RAGPipeline:
    def __init__(self):
        self.documents = []
    
    def add_documents(self, docs):
        self.documents.extend(docs)
    
    def query(self, question):
        if not self.documents:
            return "I haven't learned anything yet! Please upload some documents to teach me. 📚"
        
        question_lower = question.lower()
        relevant_info = []
        
        for doc in self.documents:
            doc_lower = doc.lower()
            words = question_lower.split()
            for word in words:
                if len(word) > 3 and word in doc_lower:
                    relevant_info.append(doc)
                    break
        
        if relevant_info:
            context = " ".join(relevant_info[:2])
            return f"Based on what I learned: {context[:200]}..."
        
        return f"I don't have specific information about '{question}' in my knowledge base. Try asking something else! 🤔"

def create_vector_store(docs):
    return docs

def create_rag_chain(vector_store):
    return RAGPipeline()
