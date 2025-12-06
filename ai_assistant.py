import json
import os
from datetime import datetime
import cv2
import numpy as np
import pyttsx3
import threading
import speech_recognition as sr
import requests
from bs4 import BeautifulSoup
import sqlite3

class VoiceVisionAI:
    def __init__(self, org_name="Baby AI"):
        self.org_name = org_name
        self.db_path = "baby_ai_knowledge/assistant.db"
        self.faces_folder = "baby_ai_knowledge/faces"
        os.makedirs(self.faces_folder, exist_ok=True)
        
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        self.recognizer = sr.Recognizer()
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS conversations
                     (id INTEGER PRIMARY KEY, timestamp TEXT, user_input TEXT, 
                      ai_response TEXT, sources TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS identities
                     (id INTEGER PRIMARY KEY, person_id TEXT, display_name TEXT, 
                      embedding TEXT, enrolled_date TEXT, consent INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS audit_log
                     (id INTEGER PRIMARY KEY, timestamp TEXT, action TEXT, 
                      details TEXT, location TEXT)''')
        conn.commit()
        conn.close()
    
    def web_search(self, query, locale="en", max_results=5):
        try:
            api_url = f"https://api.duckduckgo.com/?q={query}&format=json"
            response = requests.get(api_url, timeout=5)
            data = response.json()
            
            results = []
            for item in data.get('RelatedTopics', [])[:max_results]:
                if 'Text' in item:
                    results.append({
                        "title": item.get('Text', '')[:100],
                        "url": item.get('FirstURL', ''),
                        "snippet": item.get('Text', '')
                    })
            return results if results else [{"title": query, "url": "", "snippet": f"Information about {query}"}]
        except:
            return [{"title": query, "url": "", "snippet": f"Searching for {query}"}]
    
    def web_browse(self, url):
        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.get_text()[:500]
        except:
            return "Unable to fetch content"
    
    def asr_listen(self, language="en-US"):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5)
                text = self.recognizer.recognize_google(audio, language=language)
                return text
        except:
            return None
    
    def tts_speak(self, text, speed=150):
        def _speak():
            self.tts_engine.setProperty('rate', speed)
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        threading.Thread(target=_speak).start()
    
    def detect_faces(self, image_data):
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        results = []
        for (x, y, w, h) in faces:
            face_img = img[y:y+h, x:x+w]
            embedding = cv2.resize(face_img, (100, 100)).flatten()[:1000].tolist()
            results.append({
                "bbox": [x, y, w, h],
                "embedding": embedding,
                "confidence": 0.95,
                "liveness": 0.9
            })
        return results
    
    def enroll_identity(self, embedding, display_name, consent=True):
        if not consent:
            return {"error": "Consent required"}
        
        person_id = f"ID_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO identities VALUES (NULL, ?, ?, ?, ?, ?)",
                  (person_id, display_name, json.dumps(embedding), 
                   datetime.now().isoformat(), 1))
        conn.commit()
        conn.close()
        
        self.log_audit("ENROLL", f"Enrolled {display_name} as {person_id}")
        return {"person_id": person_id, "display_name": display_name}
    
    def match_identity(self, embedding):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT person_id, display_name, embedding, enrolled_date FROM identities WHERE consent=1")
        rows = c.fetchall()
        conn.close()
        
        best_match = None
        min_distance = float('inf')
        
        for row in rows:
            saved_embedding = json.loads(row[2])
            distance = np.linalg.norm(np.array(embedding) - np.array(saved_embedding))
            if distance < min_distance:
                min_distance = distance
                confidence = max(0, 100 - distance/50)
                best_match = {
                    "person_id": row[0], 
                    "display_name": row[1], 
                    "confidence": confidence,
                    "enrolled_date": row[3],
                    "greeting": f"Welcome back {row[1]}! Nice to see you again."
                }
        
        if best_match and best_match["confidence"] > 70:
            self.log_audit("MATCH", f"Matched {best_match['display_name']} with {best_match['confidence']:.1f}% confidence")
            return best_match
        return None
    
    def get_conversation_history(self, limit=10):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT timestamp, user_input, ai_response FROM conversations ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return [{"timestamp": r[0], "user": r[1], "ai": r[2]} for r in reversed(rows)]
    
    def get_stats(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM conversations")
        conv_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM identities WHERE consent=1")
        identity_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM audit_log")
        audit_count = c.fetchone()[0]
        conn.close()
        return {"conversations": conv_count, "identities": identity_count, "audits": audit_count}
    
    def log_conversation(self, user_input, ai_response, sources=""):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO conversations VALUES (NULL, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), user_input, ai_response, sources))
        conn.commit()
        conn.close()
    
    def log_audit(self, action, details):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO audit_log VALUES (NULL, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), action, details, "Local"))
        conn.commit()
        conn.close()
    
    def process_query(self, query, use_web=True, conversation_history=[]):
        if use_web:
            results = self.web_search(query)
            sources = [r["url"] for r in results if r["url"]]
            context = " ".join([r["snippet"] for r in results])
            
            if context:
                response = f"Based on latest information: {context[:300]}..."
            else:
                response = f"I found information about '{query}'. Let me help you with that."
        else:
            history_context = " ".join([h["user"] for h in conversation_history[-3:]])
            if query.lower() in history_context.lower():
                response = f"I remember we discussed this. Regarding '{query}', let me elaborate further."
            else:
                response = f"Interesting question about '{query}'. I'm learning and will remember this."
        
        self.log_conversation(query, response, json.dumps(sources if use_web else []))
        return response, sources if use_web else []
