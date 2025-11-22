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
from datetime import datetime
from bs4 import BeautifulSoup

class Jarvis:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)
        self.recognizer = sr.Recognizer()
        self.memory_file = 'memory.json'
        self.memory = self.load_memory()
        self.command_keywords = ['open', 'close', 'search', 'play', 'create', 'delete', 'run', 'stop', 'exit', 'time', 'what', 'how', 'show', 'volume', 'brightness', 'wifi', 'bluetooth', 'shutdown', 'restart', 'lock', 'screenshot']
        self.listening = True
    
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
    
    def search_web(self, query):
        try:
            url = f"https://api.duckduckgo.com/?q={query}&format=json"
            response = requests.get(url, timeout=3)
            data = response.json()
            if data.get('AbstractText'):
                return data['AbstractText']
            
            search_url = f"https://www.google.com/search?q={query}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(search_url, headers=headers, timeout=3)
            soup = BeautifulSoup(response.text, 'html.parser')
            result = soup.find('div', class_='BNeawe')
            return result.text if result else "I couldn't find that information"
        except:
            return "I'm having trouble accessing the web right now"
    
    def system_control(self, command):
        lower = command.lower()
        
        if 'volume up' in lower:
            pyautogui.press('volumeup', presses=5)
            return "Volume increased"
        elif 'volume down' in lower:
            pyautogui.press('volumedown', presses=5)
            return "Volume decreased"
        elif 'mute' in lower:
            pyautogui.press('volumemute')
            return "Muted"
        
        elif 'brightness up' in lower:
            subprocess.run('powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,100)', shell=True)
            return "Brightness increased"
        elif 'brightness down' in lower:
            subprocess.run('powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,30)', shell=True)
            return "Brightness decreased"
        
        elif 'wifi off' in lower:
            subprocess.run('netsh interface set interface "Wi-Fi" disabled', shell=True)
            return "WiFi disabled"
        elif 'wifi on' in lower:
            subprocess.run('netsh interface set interface "Wi-Fi" enabled', shell=True)
            return "WiFi enabled"
        
        elif 'screenshot' in lower:
            screenshot = pyautogui.screenshot()
            screenshot.save(f'screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            return "Screenshot saved"
        
        elif 'lock' in lower:
            subprocess.run('rundll32.exe user32.dll,LockWorkStation', shell=True)
            return "Locking computer"
        
        elif 'shutdown' in lower:
            subprocess.run('shutdown /s /t 5', shell=True)
            return "Shutting down in 5 seconds"
        
        elif 'restart' in lower:
            subprocess.run('shutdown /r /t 5', shell=True)
            return "Restarting in 5 seconds"
        
        elif 'running apps' in lower or 'processes' in lower:
            apps = [p.name() for p in psutil.process_iter()[:5]]
            return f"Running: {', '.join(apps)}"
        
        return None
    
    def execute_action(self, command):
        lower = command.lower()
        
        # System control
        sys_response = self.system_control(command)
        if sys_response:
            return sys_response
        
        # App control
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
        
        # Web actions
        elif 'search' in lower:
            query = lower.split('search')[-1].strip()
            webbrowser.open(f'https://www.google.com/search?q={query}')
            return f"Searching for {query}"
        
        elif 'play' in lower:
            query = lower.split('play')[-1].strip()
            webbrowser.open(f'https://www.youtube.com/results?search_query={query}')
            return f"Playing {query}"
        
        # Knowledge queries
        elif any(word in lower for word in ['what is', 'who is', 'where is', 'when is', 'how to', 'why']):
            # Check memory first
            for key in self.memory:
                if any(word in key.lower() for word in lower.split()):
                    return self.memory[key]
            # Search web
            result = self.search_web(command)
            self.memory[command] = result
            self.save_memory()
            return result
        
        elif 'time' in lower:
            return datetime.now().strftime("It's %I:%M %p")
        
        elif 'what do you know' in lower or 'tell me about' in lower:
            topic = lower.split('about')[-1].strip() if 'about' in lower else lower.split('know')[-1].strip()
            for key in self.memory:
                if topic in key.lower():
                    return self.memory[key]
            result = self.search_web(topic)
            return result
        
        elif 'correct' in lower or 'wrong' in lower or 'actually' in lower:
            self.speak("What's the correct information?")
            correction = self.listen()
            if correction:
                key, value = self.extract_knowledge(correction)
                self.memory[key] = value
                self.save_memory()
                return "Got it, I've updated my memory"
            return "I didn't catch that"
        
        elif 'stop listening' in lower or 'pause' in lower:
            self.listening = False
            return "I'll stop listening. Say 'hey Jarvis' to wake me"
        
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
    
    def continuous_listen(self):
        while True:
            if not self.listening:
                text = self.listen()
                if text and 'hey jarvis' in text.lower():
                    self.listening = True
                    self.speak("Yes, I'm here")
                continue
            
            text = self.listen()
            if text:
                if not self.process(text):
                    break
    
    def run(self):
        self.speak("JARVIS fully operational. All systems online. I'm always listening")
        self.continuous_listen()

if __name__ == "__main__":
    jarvis = Jarvis()
    jarvis.run()
