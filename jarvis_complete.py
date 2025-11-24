"""
JARVIS - Complete AI Voice Assistant
Production-Ready All-in-One Edition
Version: 2.0 Final
"""

import speech_recognition as sr
import pyttsx3
import subprocess
import os
import json
import webbrowser
import requests
import psutil
import pyautogui
import threading
import random
import ast
import operator
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

try:
    import wikipedia
except:
    wikipedia = None

try:
    import pyjokes
except:
    pyjokes = None

try:
    import pyperclip
except:
    pyperclip = None

try:
    import cv2
    import face_recognition
    import numpy as np
    import pickle
    VISION_AVAILABLE = True
except:
    VISION_AVAILABLE = False

class VisionModule:
    def __init__(self):
        if not VISION_AVAILABLE:
            return
        self.camera = None
        self.known_faces = {}
        self.faces_file = 'known_faces.pkl'
        self.load_known_faces()
        
    def load_known_faces(self):
        try:
            if os.path.exists(self.faces_file):
                with open(self.faces_file, 'rb') as f:
                    self.known_faces = pickle.load(f)
        except:
            self.known_faces = {}
    
    def save_known_faces(self):
        try:
            with open(self.faces_file, 'wb') as f:
                pickle.dump(self.known_faces, f)
        except:
            pass
    
    def start_camera(self):
        try:
            if self.camera is None:
                self.camera = cv2.VideoCapture(0)
            return self.camera.isOpened()
        except:
            return False
    
    def stop_camera(self):
        try:
            if self.camera:
                self.camera.release()
                cv2.destroyAllWindows()
                self.camera = None
        except:
            pass
    
    def capture_frame(self):
        try:
            if not self.start_camera():
                return None
            ret, frame = self.camera.read()
            return frame if ret else None
        except:
            return None
    
    def detect_faces(self, frame):
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            return face_locations, face_encodings
        except:
            return [], []
    
    def recognize_face(self, face_encoding):
        try:
            if not self.known_faces:
                return "Unknown"
            
            for name, known_encoding in self.known_faces.items():
                matches = face_recognition.compare_faces([known_encoding], face_encoding, tolerance=0.6)
                if matches[0]:
                    return name
            return "Unknown"
        except:
            return "Unknown"
    
    def learn_face(self, name):
        try:
            frame = self.capture_frame()
            if frame is None:
                return False
            
            face_locations, face_encodings = self.detect_faces(frame)
            
            if len(face_encodings) == 0:
                return False
            
            self.known_faces[name] = face_encodings[0]
            self.save_known_faces()
            cv2.imwrite(f"face_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg", frame)
            return True
        except:
            return False
    
    def who_am_i_seeing(self):
        try:
            frame = self.capture_frame()
            if frame is None:
                return "Camera not available"
            
            face_locations, face_encodings = self.detect_faces(frame)
            
            if len(face_encodings) == 0:
                return "No faces detected"
            
            names = [self.recognize_face(enc) for enc in face_encodings]
            
            if len(names) == 1:
                return f"I see {names[0]}"
            else:
                return f"I see {len(names)} people: {', '.join(names)}"
        except:
            return "Error accessing camera"
    
    def show_camera_feed(self, duration=5):
        try:
            if not self.start_camera():
                return False
            
            start_time = datetime.now()
            while (datetime.now() - start_time).seconds < duration:
                frame = self.capture_frame()
                if frame is None:
                    break
                
                face_locations, face_encodings = self.detect_faces(frame)
                
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    name = self.recognize_face(face_encoding)
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                
                cv2.imshow('JARVIS Vision', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            cv2.destroyAllWindows()
            return True
        except:
            return False
    
    def take_photo(self):
        try:
            frame = self.capture_frame()
            if frame is None:
                return None
            
            filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(filename, frame)
            return filename
        except:
            return None
    
    def describe_scene(self):
        try:
            frame = self.capture_frame()
            if frame is None:
                return "Camera not available"
            
            face_locations, _ = self.detect_faces(frame)
            brightness = np.mean(frame)
            
            description = []
            
            if brightness < 50:
                description.append("The scene is dark")
            elif brightness > 200:
                description.append("The scene is very bright")
            else:
                description.append("The scene has normal lighting")
            
            if len(face_locations) > 0:
                description.append(f"I detect {len(face_locations)} face(s)")
            else:
                description.append("No faces detected")
            
            return ". ".join(description)
        except:
            return "Error analyzing scene"

class Jarvis:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            voices = self.engine.getProperty('voices')
            if voices:
                self.engine.setProperty('voice', voices[0].id)
            self.engine.setProperty('rate', 190)
            self.engine.setProperty('volume', 1.0)
        except:
            self.engine = None
            print("[Warning] Text-to-speech not available")
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True
        self.memory_file = 'memory.json'
        self.memory = self.load_memory()
        self.listening = True
        self.current_language = 'en'
        self.context = []
        self.reminders = []
        self.user_name = self.memory.get('user_name', 'Sir')
        self.vision = VisionModule() if VISION_AVAILABLE else None
        
        # Safe math operators
        self.safe_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.USub: operator.neg
        }
    
    def speak(self, text, lang=None):
        try:
            if lang is None:
                lang = self.current_language
            
            if lang == 'ne':
                try:
                    nepali_text = GoogleTranslator(source='en', target='ne').translate(text)
                    print(f"जार्विस: {nepali_text}")
                except:
                    print(f"JARVIS: {text}")
            else:
                print(f"JARVIS: {text}")
            
            if self.engine:
                self.engine.say(text)
                self.engine.runAndWait()
        except Exception as e:
            print(f"JARVIS: {text}")
    
    def listen(self):
        try:
            with sr.Microphone() as source:
                print("सुन्दै छु... / Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                except sr.WaitTimeoutError:
                    return ""
            
            try:
                text = self.recognizer.recognize_google(audio, language='en-US')
                print(f"You: {text}")
                self.current_language = 'en'
                self.context.append(text)
                return text
            except:
                try:
                    text = self.recognizer.recognize_google(audio, language='ne-NP')
                    print(f"तपाईं: {text}")
                    self.current_language = 'ne'
                    self.context.append(text)
                    return text
                except:
                    return ""
        except Exception as e:
            print(f"[Error] Microphone: {e}")
            return ""
    
    def load_memory(self):
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save_memory(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def translate_to_english(self, text):
        if self.current_language == 'ne':
            try:
                return GoogleTranslator(source='ne', target='en').translate(text)
            except:
                return text
        return text
    
    def safe_eval_expr(self, node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            left = self.safe_eval_expr(node.left)
            right = self.safe_eval_expr(node.right)
            return self.safe_operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self.safe_eval_expr(node.operand)
            return self.safe_operators[type(node.op)](operand)
        else:
            raise ValueError("Unsupported operation")
    
    def safe_calculate(self, expr):
        try:
            expr = expr.replace('^', '**')
            node = ast.parse(expr, mode='eval')
            return self.safe_eval_expr(node.body)
        except:
            return None
    
    def search_web(self, query):
        try:
            if wikipedia:
                try:
                    result = wikipedia.summary(query, sentences=3, auto_suggest=True)
                    if result and len(result) > 20:
                        self.learn(query, result)
                        return result
                except wikipedia.exceptions.DisambiguationError as e:
                    try:
                        result = wikipedia.summary(e.options[0], sentences=2)
                        self.learn(query, result)
                        return result
                    except:
                        pass
                except:
                    pass
            
            url = f"https://api.duckduckgo.com/?q={query}&format=json"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if data.get('AbstractText'):
                answer = data['AbstractText']
                self.learn(query, answer)
                return answer
            
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
            response = requests.get(wiki_url, timeout=5)
            if response.status_code == 200:
                wiki_data = response.json()
                if wiki_data.get('extract'):
                    answer = wiki_data['extract']
                    self.learn(query, answer)
                    return answer
            
            search_url = f"https://www.google.com/search?q={query}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(search_url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            selectors = [('div', 'BNeawe'), ('span', 'hgKElc'), ('div', 'kCrYT')]
            
            for tag, class_name in selectors:
                snippet = soup.find(tag, class_=class_name)
                if snippet and len(snippet.text) > 20:
                    answer = snippet.text
                    self.learn(query, answer)
                    return answer
            
            return "I couldn't find reliable information. Opening browser."
        except Exception as e:
            return "I'm having trouble accessing the web"
    
    def get_weather(self, city=""):
        try:
            if not city:
                city = self.memory.get('user_location', 'Kathmandu')
            url = f"https://wttr.in/{city}?format=%C+%t+%w"
            response = requests.get(url, timeout=5)
            return f"Weather in {city}: {response.text}"
        except:
            return "Couldn't fetch weather"
    
    def get_news(self):
        try:
            url = "https://news.google.com/rss"
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item')[:5]
            news = [item.title.text for item in items]
            return "Top news: " + ". ".join(news[:3])
        except:
            return "Couldn't fetch news"
    
    def learn(self, key, value):
        try:
            self.memory[key.lower()] = value
            self.save_memory()
            print(f"[LEARNED] {key[:50]}...")
        except:
            pass
    
    def recall(self, query):
        try:
            query_lower = query.lower()
            if query_lower in self.memory:
                return self.memory[query_lower]
            for key in self.memory:
                if query_lower in key or key in query_lower:
                    return self.memory[key]
        except:
            pass
        return None
    
    def execute_action(self, command):
        lower = command.lower()
        
        try:
            # Vision commands
            if self.vision and VISION_AVAILABLE:
                if 'who am i seeing' in lower or 'who do you see' in lower:
                    return self.vision.who_am_i_seeing()
                elif 'learn my face' in lower or 'remember my face' in lower:
                    self.speak("Please look at the camera")
                    if self.vision.learn_face(self.user_name):
                        return f"I've learned your face, {self.user_name}"
                    return "Couldn't detect your face"
                elif 'learn face' in lower:
                    self.speak("What is this person's name?")
                    name = self.listen()
                    if name:
                        self.speak(f"Please {name}, look at the camera")
                        if self.vision.learn_face(name):
                            return f"I've learned {name}'s face"
                    return "Couldn't detect face"
                elif 'take photo' in lower or 'take picture' in lower:
                    filename = self.vision.take_photo()
                    if filename:
                        return f"Photo saved as {filename}"
                    return "Couldn't take photo"
                elif 'show camera' in lower or 'open camera' in lower:
                    self.speak("Opening camera. Press Q to close")
                    self.vision.show_camera_feed(duration=30)
                    return "Camera closed"
                elif 'describe scene' in lower or 'what do you see' in lower:
                    return self.vision.describe_scene()
                elif 'stop camera' in lower:
                    self.vision.stop_camera()
                    return "Camera stopped"
            
            # System control
            if 'volume up' in lower:
                pyautogui.press('volumeup', presses=5)
                return "Volume increased"
            elif 'volume down' in lower:
                pyautogui.press('volumedown', presses=5)
                return "Volume decreased"
            elif 'mute' in lower:
                pyautogui.press('volumemute')
                return "Volume toggled"
            elif 'screenshot' in lower:
                screenshot = pyautogui.screenshot()
                filename = f'screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
                screenshot.save(filename)
                return f"Screenshot saved as {filename}"
            elif 'lock' in lower and 'computer' in lower:
                subprocess.run('rundll32.exe user32.dll,LockWorkStation', shell=True)
                return "Locking computer"
            elif 'shutdown' in lower:
                subprocess.run('shutdown /s /t 5', shell=True)
                return "Shutting down in 5 seconds"
            elif 'restart' in lower:
                subprocess.run('shutdown /r /t 5', shell=True)
                return "Restarting in 5 seconds"
            elif 'battery' in lower:
                battery = psutil.sensors_battery()
                if battery:
                    return f"Battery at {battery.percent}%, {'charging' if battery.power_plugged else 'not charging'}"
                return "Battery info not available"
            elif 'cpu' in lower:
                cpu = psutil.cpu_percent(interval=1)
                return f"CPU usage is {cpu}%"
            elif 'memory' in lower or 'ram' in lower:
                mem = psutil.virtual_memory()
                return f"Memory usage is {mem.percent}%, {mem.available // (1024**3)} GB available"
            
            # App control
            elif 'open' in lower:
                app = lower.split('open')[-1].strip()
                app_map = {
                    'chrome': 'chrome', 'browser': 'chrome', 'notepad': 'notepad',
                    'calculator': 'calc', 'paint': 'mspaint', 'explorer': 'explorer',
                    'cmd': 'cmd', 'terminal': 'cmd'
                }
                app_to_open = app_map.get(app, app)
                subprocess.Popen(app_to_open, shell=True)
                return f"Opening {app}"
            
            # Web actions
            elif 'search' in lower or 'google' in lower:
                query = lower.replace('search', '').replace('google', '').replace('for', '').strip()
                if any(word in lower for word in ['what', 'who', 'where', 'when', 'how', 'why']):
                    remembered = self.recall(query)
                    if remembered:
                        return f"I remember: {remembered}"
                    self.speak("Searching the web")
                    result = self.search_web(query)
                    if "couldn't find" in result.lower() or "browser" in result.lower():
                        webbrowser.open(f'https://www.google.com/search?q={query}')
                        return f"Opened browser search for {query}"
                    return result
                else:
                    webbrowser.open(f'https://www.google.com/search?q={query}')
                    return f"Searching for {query}"
            
            elif 'play' in lower:
                query = lower.split('play')[-1].strip()
                webbrowser.open(f'https://www.youtube.com/results?search_query={query}')
                return f"Playing {query}"
            
            elif any(word in lower for word in ['what is', 'who is', 'where is', 'how to', 'why', 'define']):
                remembered = self.recall(command)
                if remembered:
                    return f"I remember: {remembered}"
                self.speak("Searching the web")
                result = self.search_web(command)
                if "couldn't find" in result.lower() or "browser" in result.lower():
                    webbrowser.open(f'https://www.google.com/search?q={command}')
                    return "Opened browser search"
                return result
            
            # Utilities
            elif 'time' in lower:
                return datetime.now().strftime("It's %I:%M %p")
            elif 'date' in lower:
                return datetime.now().strftime("Today is %A, %B %d, %Y")
            elif 'calculate' in lower or 'math' in lower:
                expr = lower.replace('calculate', '').replace('math', '').replace('what is', '').strip()
                expr = expr.replace('plus', '+').replace('minus', '-').replace('times', '*').replace('divided by', '/')
                expr = expr.replace('multiply', '*').replace('divide', '/')
                result = self.safe_calculate(expr)
                if result is not None:
                    return f"The answer is {result}"
                return "I couldn't calculate that"
            elif 'joke' in lower:
                if pyjokes:
                    return pyjokes.get_joke()
                jokes = ["Why do programmers prefer dark mode? Because light attracts bugs!",
                        "Why did the AI go to school? To improve its learning rate!"]
                return random.choice(jokes)
            elif 'weather' in lower:
                city = lower.split('in')[-1].strip() if 'in' in lower else ""
                return self.get_weather(city)
            elif 'news' in lower:
                return self.get_news()
            elif 'location' in lower or 'where am i' in lower:
                response = requests.get('https://ipapi.co/json/', timeout=3)
                data = response.json()
                location = f"{data.get('city', 'Unknown')}, {data.get('country_name', 'Unknown')}"
                self.memory['user_location'] = data.get('city', 'Unknown')
                self.save_memory()
                return f"You are in {location}"
            elif 'ip address' in lower:
                response = requests.get('https://api.ipify.org', timeout=3)
                return f"Your IP address is {response.text}"
            
            # Learning
            elif 'my name is' in lower or "i'm" in lower or 'i am' in lower:
                name = lower.split('is')[-1].strip() if 'is' in lower else lower.split("i'm")[-1].strip()
                self.user_name = name
                self.memory['user_name'] = name
                self.save_memory()
                return f"Nice to meet you, {name}"
            
            elif 'stop listening' in lower or 'sleep' in lower:
                self.listening = False
                return f"Going to sleep. Say 'hey Jarvis' to wake me"
            elif 'stop' in lower or 'exit' in lower or 'quit' in lower:
                return None
            
            return "I'm not sure how to help with that"
        
        except Exception as e:
            print(f"[Error] {e}")
            return "I encountered an error processing that command"
    
    def process(self, text):
        if not text:
            return True
        
        try:
            english_text = self.translate_to_english(text)
            response = self.execute_action(english_text)
            
            if response is None:
                self.speak("Shutting down", self.current_language)
                return False
            
            self.speak(response, self.current_language)
            return True
        except Exception as e:
            print(f"[Error] Processing: {e}")
            return True
    
    def continuous_listen(self):
        error_count = 0
        while True:
            try:
                if not self.listening:
                    text = self.listen()
                    if text:
                        lower = text.lower()
                        if 'hey jarvis' in lower or 'jarvis' in lower:
                            self.listening = True
                            self.speak("Yes, I'm here")
                            error_count = 0
                    continue
                
                text = self.listen()
                if text:
                    if not self.process(text):
                        break
                    error_count = 0
                else:
                    error_count += 1
                    if error_count > 10:
                        print("[Warning] Check microphone")
                        error_count = 0
            except Exception as e:
                print(f"[Error] {e}")
                error_count += 1
                if error_count > 5:
                    print("[Critical] Too many errors")
                    break
    
    def run(self):
        try:
            greeting = f"JARVIS fully operational. Ready to assist, {self.user_name}"
            self.speak(greeting)
            print("\n" + "="*70)
            print("JARVIS - Complete AI Assistant")
            print("Bilingual: English | Nepali (नेपाली)")
            print("Features: Voice | Vision | System Control | Web Search | Learning")
            if VISION_AVAILABLE:
                print("Vision: ✓ Enabled")
            else:
                print("Vision: ✗ Disabled (install opencv-python face-recognition)")
            print("="*70 + "\n")
            self.continuous_listen()
        except KeyboardInterrupt:
            self.speak("Shutting down gracefully")
            print("\n[✓] JARVIS stopped")
        except Exception as e:
            print(f"\n[✗] Fatal error: {e}")
            self.speak("Critical error. Shutting down")

if __name__ == "__main__":
    try:
        jarvis = Jarvis()
        jarvis.run()
    except Exception as e:
        print(f"Failed to start JARVIS: {e}")
        input("Press Enter to exit...")
