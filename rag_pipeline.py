import json
import os
from datetime import datetime
import cv2
import numpy as np
import pyttsx3
import threading

class RAGPipeline:
    def __init__(self):
        self.folder = "baby_ai_knowledge"
        self.learned_file = os.path.join(self.folder, "learned.json")
        self.faces_folder = os.path.join(self.folder, "faces")
        os.makedirs(self.folder, exist_ok=True)
        os.makedirs(self.faces_folder, exist_ok=True)
        self.data = self.load_data()
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)
    
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
    
    def detect_and_save_face(self, image_data, name="unknown"):
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            return None, "No face detected"
        
        face_id = f"face_{len(self.data['faces'])}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        face_path = os.path.join(self.faces_folder, face_id)
        
        for (x, y, w, h) in faces:
            face_img = img[y:y+h, x:x+w]
            cv2.imwrite(face_path, face_img)
            
            face_encoding = self.encode_face(face_img)
            self.data["faces"].append({
                "id": face_id,
                "name": name,
                "path": face_path,
                "encoding": face_encoding.tolist(),
                "timestamp": datetime.now().isoformat()
            })
            break
        
        self.save_data()
        return face_id, f"Detected {len(faces)} face(s)"
    
    def encode_face(self, face_img):
        resized = cv2.resize(face_img, (100, 100))
        return resized.flatten()[:1000]
    
    def recognize_face(self, image_data):
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            return "No face detected"
        
        for (x, y, w, h) in faces:
            face_img = img[y:y+h, x:x+w]
            encoding = self.encode_face(face_img)
            
            best_match = None
            min_distance = float('inf')
            
            for saved_face in self.data["faces"]:
                distance = np.linalg.norm(np.array(encoding) - np.array(saved_face["encoding"]))
                if distance < min_distance:
                    min_distance = distance
                    best_match = saved_face
            
            if best_match and min_distance < 5000:
                return f"Recognized: {best_match['name']} (confidence: {100 - min_distance/100:.1f}%)"
        
        return "Unknown person"
    
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
    
    def speak(self, text):
        def _speak():
            self.engine.say(text)
            self.engine.runAndWait()
        thread = threading.Thread(target=_speak)
        thread.start()
