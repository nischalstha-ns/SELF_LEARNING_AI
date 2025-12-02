import json
import os

class RAGPipeline:
    def __init__(self):
        self.knowledge_folder = "baby_ai_knowledge"
        self.knowledge_file = os.path.join(self.knowledge_folder, "learned_data.json")
        os.makedirs(self.knowledge_folder, exist_ok=True)
        self.documents = self.load_documents()
    
    def load_documents(self):
        if os.path.exists(self.knowledge_file):
            with open(self.knowledge_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    
    def save_documents(self):
        with open(self.knowledge_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
    
    def add_documents(self, docs):
        self.documents.extend(docs)
        self.save_documents()
    
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
