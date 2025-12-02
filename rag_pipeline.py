import json
import os
from datetime import datetime

class RAGPipeline:
    def __init__(self):
        self.folder = "baby_ai_knowledge"
        self.learned_file = os.path.join(self.folder, "learned.json")
        self.faces_folder = os.path.join(self.folder, "faces")
        os.makedirs(self.folder, exist_ok=True)
        os.makedirs(self.faces_folder, exist_ok=True)
        self.data = self.load_data()
    
    def load_data(self):
        if os.path.exists(self.learned_file):
            with open(self.learned_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"conversations": [], "knowledge": [], "faces": []}
    
    def save_data(self):
        with open(self.learned_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def learn_conversation(self, user_msg, ai_response):
        self.data["conversations"].append({
            "timestamp": datetime.now().isoformat(),
            "user": user_msg,
            "ai": ai_response
        })
        self.data["knowledge"].append(user_msg)
        self.save_data()
    
    def save_face(self, image_data, name="unknown"):
        face_id = f"face_{len(self.data['faces'])}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        face_path = os.path.join(self.faces_folder, face_id)
        with open(face_path, "wb") as f:
            f.write(image_data)
        self.data["faces"].append({"id": face_id, "name": name, "path": face_path})
        self.save_data()
        return face_id
    
    def query(self, question):
        if not self.data["knowledge"]:
            response = "Hi! I'm Baby AI. I'm learning from scratch. Tell me anything!"
        else:
            question_lower = question.lower()
            relevant = []
            for conv in self.data["conversations"][-10:]:
                if any(word in conv["user"].lower() for word in question_lower.split() if len(word) > 3):
                    relevant.append(conv["ai"])
            
            if relevant:
                response = f"I remember something similar: {relevant[-1][:150]}..."
            else:
                response = f"Interesting! I'm learning about '{question}'. Let me remember this."
        
        self.learn_conversation(question, response)
        return response
