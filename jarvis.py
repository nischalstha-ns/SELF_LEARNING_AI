import speech_recognition as sr
import pyttsx3
import subprocess
import os
import json
import webbrowser
from datetime import datetime

class Jarvis:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)
        self.recognizer = sr.Recognizer()
        self.memory_file = 'memory.json'
        self.memory = self.load_memory()
        self.command_keywords = ['open', 'close', 'search', 'play', 'create', 'delete', 'run', 'stop', 'exit', 'time', 'what', 'how', 'show']
    
    def speak(self, text):
        print(f"JARVIS: {text}")
        self.engine.say(text)
        self.engine.runAndWait()
    
    def listen(self):
        with sr.Microphone() as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = self.recognizer.listen(source)
        try:
            text = self.recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text
        except:
            return ""
    
    def load_memory(self):
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_memory(self):
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)
    
    def detect_intent(self, text):
        lower = text.lower()
        for keyword in self.command_keywords:
            if keyword in lower:
                return 'command'
        if any(word in lower for word in ['my', 'i am', "i'm", 'is', 'are', 'was']):
            return 'knowledge'
        return 'command'
    
    def extract_knowledge(self, text):
        lower = text.lower()
        if 'my name is' in lower or "i'm" in lower or 'i am' in lower:
            key = 'user_name'
            value = text.split('is')[-1].strip() if 'is' in lower else text.split("i'm")[-1].strip() if "i'm" in lower else text.split('am')[-1].strip()
        elif 'my' in lower:
            parts = lower.split('my', 1)[1].split('is')
            key = parts[0].strip() if len(parts) > 0 else 'info'
            value = parts[1].strip() if len(parts) > 1 else text
        else:
            key = datetime.now().isoformat()
            value = text
        return key, value
    
    def execute_action(self, command):
        lower = command.lower()
        
        if 'open' in lower:
            app = lower.split('open')[-1].strip()
            try:
                subprocess.Popen(app, shell=True)
                return f"Opening {app}"
            except:
                return f"Couldn't open {app}"
        
        elif 'close' in lower:
            app = lower.split('close')[-1].strip()
            subprocess.run(f'taskkill /IM {app}.exe /F', shell=True, capture_output=True)
            return f"Closing {app}"
        
        elif 'search' in lower:
            query = lower.split('search')[-1].strip()
            webbrowser.open(f'https://www.google.com/search?q={query}')
            return f"Searching for {query}"
        
        elif 'play' in lower:
            query = lower.split('play')[-1].strip()
            webbrowser.open(f'https://www.youtube.com/results?search_query={query}')
            return f"Playing {query}"
        
        elif 'time' in lower:
            return datetime.now().strftime("It's %I:%M %p")
        
        elif 'what do you know' in lower or 'tell me about' in lower:
            topic = lower.split('about')[-1].strip() if 'about' in lower else lower.split('know')[-1].strip()
            for key in self.memory:
                if topic in key.lower():
                    return self.memory[key]
            return "I don't have that information"
        
        elif 'correct' in lower or 'wrong' in lower or 'actually' in lower:
            self.speak("What's the correct information?")
            correction = self.listen()
            if correction:
                key, value = self.extract_knowledge(correction)
                self.memory[key] = value
                self.save_memory()
                return "Got it, I've updated my memory"
            return "I didn't catch that"
        
        elif 'stop' in lower or 'exit' in lower or 'quit' in lower:
            return None
        
        return "I'm not sure how to help with that. Can you rephrase?"
    
    def process(self, text):
        if not text:
            return True
        
        intent = self.detect_intent(text)
        
        if intent == 'knowledge':
            key, value = self.extract_knowledge(text)
            self.memory[key] = value
            self.save_memory()
            response = f"Understood, I'll remember that"
        else:
            response = self.execute_action(text)
            if response is None:
                self.speak("Shutting down")
                return False
        
        self.speak(response)
        return True
    
    def run(self):
        self.speak("JARVIS online. How can I help you?")
        while True:
            text = self.listen()
            if not self.process(text):
                break

if __name__ == "__main__":
    jarvis = Jarvis()
    jarvis.run()
