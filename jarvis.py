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
import re
import shutil
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
try:
    import wikipedia
    import pyjokes
    import pyperclip
except:
    pass

class Jarvis:
    def __init__(self):
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[0].id if voices else None)
        self.engine.setProperty('rate', 190)
        self.engine.setProperty('volume', 1.0)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True
        self.memory_file = 'memory.json'
        self.memory = self.load_memory()
        self.command_keywords = ['open', 'close', 'search', 'play', 'create', 'delete', 'run', 'stop', 'exit', 'time', 'what', 'how', 'show', 'volume', 'brightness', 'wifi', 'bluetooth', 'shutdown', 'restart', 'lock', 'screenshot', 'write', 'note', 'remind', 'calculate']
        self.nepali_keywords = ['खोल्नुहोस्', 'बन्द', 'खोज', 'बजाउनुहोस्', 'समय', 'के', 'कसरी', 'भोल्युम', 'वाइफाइ', 'स्क्रिनशट', 'बन्द गर्नुहोस्', 'रिस्टार्ट']
        self.listening = True
        self.current_language = 'en'
        self.context = []
        self.reminders = []
        self.user_name = self.memory.get('user_name', 'Sir')
    
    def speak(self, text, lang=None):
        try:
            if lang is None:
                lang = self.current_language
            
            if lang == 'ne':
                try:
                    nepali_text = GoogleTranslator(source='en', target='ne').translate(text)
                    print(f"जार्विस: {nepali_text}")
                    self.engine.say(text)
                    self.engine.runAndWait()
                except:
                    print(f"JARVIS: {text}")
                    self.engine.say(text)
                    self.engine.runAndWait()
            else:
                print(f"JARVIS: {text}")
                self.engine.say(text)
                self.engine.runAndWait()
        except Exception as e:
            print(f"JARVIS: {text}")
            print(f"[Error] Speech engine: {e}")
    
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
            print(f"[Error] Microphone issue: {e}")
            return ""
    
    def load_memory(self):
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_memory(self):
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)
    
    def translate_to_english(self, text):
        if self.current_language == 'ne':
            try:
                return GoogleTranslator(source='ne', target='en').translate(text)
            except:
                return text
        return text
    
    def detect_intent(self, text):
        english_text = self.translate_to_english(text)
        lower = english_text.lower()
        
        for keyword in self.command_keywords:
            if keyword in lower:
                return 'command'
        if any(word in lower for word in ['my', 'i am', "i'm", 'is', 'are', 'was', 'मेरो', 'म']):
            return 'knowledge'
        return 'command'
    
    def extract_knowledge(self, text):
        lower = text.lower()
        if 'my name is' in lower or "i'm" in lower or 'i am' in lower:
            key = 'user_name'
            value = text.split('is')[-1].strip() if 'is' in lower else text.split("i'm")[-1].strip() if "i'm" in lower else text.split('am')[-1].strip()
            self.user_name = value
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
            
            snippet = soup.find('div', class_='BNeawe') or soup.find('span', class_='hgKElc')
            if snippet:
                answer = snippet.text
                if len(answer) > 20:
                    self.learn(query, answer)
                    return answer
            
            return "I couldn't find reliable information about that. Try rephrasing your question."
        except Exception as e:
            print(f"[Error] Web search failed: {e}")
            return "I'm having trouble accessing the web right now"
    
    def get_weather(self, city=""):
        try:
            if not city:
                city = self.memory.get('user_location', 'Kathmandu')
            url = f"https://wttr.in/{city}?format=%C+%t+%w"
            response = requests.get(url, timeout=5)
            return f"Weather in {city}: {response.text}"
        except:
            return "Couldn't fetch weather information"
    
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
    
    def file_operations(self, command):
        lower = command.lower()
        
        if 'create folder' in lower or 'make folder' in lower:
            folder_name = lower.split('folder')[-1].strip()
            try:
                os.makedirs(folder_name, exist_ok=True)
                return f"Folder {folder_name} created"
            except:
                return "Couldn't create folder"
        
        elif 'delete file' in lower or 'remove file' in lower:
            file_name = lower.split('file')[-1].strip()
            try:
                os.remove(file_name)
                return f"File {file_name} deleted"
            except:
                return "Couldn't delete file"
        
        elif 'list files' in lower or 'show files' in lower:
            files = os.listdir('.')[:10]
            return f"Files: {', '.join(files[:5])}"
        
        return None
    
    def set_reminder(self, text):
        self.reminders.append({'text': text, 'time': datetime.now() + timedelta(minutes=5)})
        return "Reminder set for 5 minutes"
    
    def check_reminders(self):
        current_time = datetime.now()
        for reminder in self.reminders:
            if current_time >= reminder['time']:
                self.speak(f"Reminder: {reminder['text']}")
                self.reminders.remove(reminder)
    
    def learn(self, key, value):
        self.memory[key.lower()] = value
        self.save_memory()
        print(f"[LEARNED] {key[:50]}...")
    
    def recall(self, query):
        query_lower = query.lower()
        
        if query_lower in self.memory:
            return self.memory[query_lower]
        
        for key in self.memory:
            if query_lower in key or key in query_lower:
                return self.memory[key]
        
        return None
    
    def system_control(self, command):
        lower = command.lower()
        
        if 'volume up' in lower:
            pyautogui.press('volumeup', presses=5)
            return "Volume increased"
        elif 'volume down' in lower:
            pyautogui.press('volumedown', presses=5)
            return "Volume decreased"
        elif 'mute' in lower or 'unmute' in lower:
            pyautogui.press('volumemute')
            return "Volume toggled"
        
        elif 'brightness up' in lower:
            subprocess.run('powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,100)', shell=True, capture_output=True)
            return "Brightness increased"
        elif 'brightness down' in lower:
            subprocess.run('powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,30)', shell=True, capture_output=True)
            return "Brightness decreased"
        
        elif 'wifi off' in lower or 'disable wifi' in lower:
            subprocess.run('netsh interface set interface "Wi-Fi" disabled', shell=True, capture_output=True)
            return "WiFi disabled"
        elif 'wifi on' in lower or 'enable wifi' in lower:
            subprocess.run('netsh interface set interface "Wi-Fi" enabled', shell=True, capture_output=True)
            return "WiFi enabled"
        
        elif 'screenshot' in lower or 'take screenshot' in lower:
            screenshot = pyautogui.screenshot()
            filename = f'screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            screenshot.save(filename)
            return f"Screenshot saved as {filename}"
        
        elif 'lock' in lower or 'lock computer' in lower:
            subprocess.run('rundll32.exe user32.dll,LockWorkStation', shell=True)
            return "Locking computer"
        
        elif 'shutdown' in lower:
            subprocess.run('shutdown /s /t 5', shell=True)
            return "Shutting down in 5 seconds"
        
        elif 'restart' in lower or 'reboot' in lower:
            subprocess.run('shutdown /r /t 5', shell=True)
            return "Restarting in 5 seconds"
        
        elif 'cancel shutdown' in lower or 'abort shutdown' in lower:
            subprocess.run('shutdown /a', shell=True)
            return "Shutdown cancelled"
        
        elif 'running apps' in lower or 'processes' in lower or 'what is running' in lower:
            apps = [p.name() for p in psutil.process_iter()[:10]]
            return f"Top processes: {', '.join(apps[:5])}"
        
        elif 'battery' in lower or 'power' in lower:
            battery = psutil.sensors_battery()
            if battery:
                return f"Battery at {battery.percent}%, {'charging' if battery.power_plugged else 'not charging'}"
            return "Battery info not available"
        
        elif 'cpu usage' in lower or 'cpu' in lower:
            cpu = psutil.cpu_percent(interval=1)
            return f"CPU usage is {cpu}%"
        
        elif 'memory usage' in lower or 'ram' in lower:
            mem = psutil.virtual_memory()
            return f"Memory usage is {mem.percent}%, {mem.available // (1024**3)} GB available"
        
        return None
    
    def execute_action(self, command):
        lower = command.lower()
        
        self.check_reminders()
        
        file_response = self.file_operations(command)
        if file_response:
            return file_response
        
        sys_response = self.system_control(command)
        if sys_response:
            return sys_response
        
        if 'open' in lower:
            app = lower.split('open')[-1].strip()
            app_map = {
                'chrome': 'chrome', 'google': 'chrome', 'browser': 'chrome',
                'edge': 'msedge', 'firefox': 'firefox',
                'notepad': 'notepad', 'calculator': 'calc', 'paint': 'mspaint',
                'explorer': 'explorer', 'file explorer': 'explorer',
                'cmd': 'cmd', 'command prompt': 'cmd', 'terminal': 'cmd',
                'powershell': 'powershell', 'task manager': 'taskmgr',
                'settings': 'ms-settings:', 'control panel': 'control',
                'word': 'winword', 'excel': 'excel', 'powerpoint': 'powerpnt',
                'outlook': 'outlook', 'spotify': 'spotify', 'discord': 'discord',
                'vscode': 'code', 'visual studio code': 'code'
            }
            app_to_open = app_map.get(app, app)
            try:
                subprocess.Popen(app_to_open, shell=True)
                return f"Opening {app}"
            except:
                return f"Couldn't open {app}. Make sure it's installed."
        
        elif 'close' in lower:
            app = lower.split('close')[-1].strip()
            subprocess.run(f'taskkill /IM {app}.exe /F', shell=True, capture_output=True)
            return f"Closing {app}"
        
        elif 'minimize' in lower or 'hide' in lower:
            pyautogui.hotkey('win', 'd')
            return "Minimized all windows"
        
        elif 'maximize' in lower or 'restore' in lower:
            pyautogui.hotkey('win', 'd')
            return "Restored windows"
        
        elif 'search' in lower:
            query = lower.split('search')[-1].strip()
            webbrowser.open(f'https://www.google.com/search?q={query}')
            return f"Searching for {query}"
        
        elif 'play' in lower:
            query = lower.split('play')[-1].strip()
            webbrowser.open(f'https://www.youtube.com/results?search_query={query}')
            return f"Playing {query}"
        
        elif any(word in lower for word in ['what is', 'who is', 'where is', 'when is', 'how to', 'why', 'tell me', 'explain']):
            remembered = self.recall(command)
            if remembered:
                return f"I remember: {remembered}"
            
            self.speak("Let me search that for you")
            result = self.search_web(command)
            return result
        
        elif 'time' in lower:
            return datetime.now().strftime("It's %I:%M %p")
        
        elif 'date' in lower:
            return datetime.now().strftime("Today is %A, %B %d, %Y")
        
        elif 'write' in lower or 'note' in lower or 'create note' in lower:
            self.speak("What should I write?")
            note_text = self.listen()
            if note_text:
                filename = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(note_text)
                return f"Note saved as {filename}"
            return "I didn't catch that"
        
        elif 'calculate' in lower or 'math' in lower:
            try:
                expr = lower.replace('calculate', '').replace('math', '').replace('what is', '').replace('equals', '').strip()
                expr = expr.replace('plus', '+').replace('minus', '-').replace('times', '*').replace('multiply', '*')
                expr = expr.replace('divided by', '/').replace('divide', '/').replace('power', '**').replace('squared', '**2')
                expr = expr.replace('x', '*').replace('÷', '/')
                result = eval(expr, {"__builtins__": {}}, {})
                return f"The answer is {result}"
            except:
                return "I couldn't calculate that. Try using numbers and operators like plus, minus, times, divided by."
        
        elif 'joke' in lower:
            try:
                return pyjokes.get_joke()
            except:
                jokes = [
                    "Why do programmers prefer dark mode? Because light attracts bugs!",
                    "Why did the AI go to school? To improve its learning rate!",
                    "What's an AI's favorite snack? Microchips!",
                    "Why do Java developers wear glasses? Because they don't C sharp!",
                    "How many programmers does it take to change a light bulb? None, that's a hardware problem!"
                ]
                return random.choice(jokes)
        
        elif 'weather' in lower:
            city = lower.split('in')[-1].strip() if 'in' in lower else ""
            return self.get_weather(city)
        
        elif 'news' in lower:
            return self.get_news()
        
        elif 'remind me' in lower or 'reminder' in lower:
            reminder_text = lower.replace('remind me', '').replace('to', '').strip()
            return self.set_reminder(reminder_text)
        
        elif 'copy' in lower and 'clipboard' in lower:
            try:
                text = pyperclip.paste()
                return f"Clipboard contains: {text[:100]}"
            except:
                return "Couldn't access clipboard"
        
        elif 'type' in lower or 'write text' in lower:
            text = lower.replace('type', '').replace('write text', '').strip()
            pyautogui.write(text)
            return f"Typed: {text}"
        
        elif 'press' in lower:
            key = lower.split('press')[-1].strip()
            pyautogui.press(key)
            return f"Pressed {key}"
        
        elif 'location' in lower or 'where am i' in lower:
            try:
                response = requests.get('https://ipapi.co/json/', timeout=3)
                data = response.json()
                location = f"{data.get('city', 'Unknown')}, {data.get('country_name', 'Unknown')}"
                self.memory['user_location'] = data.get('city', 'Unknown')
                self.save_memory()
                return f"You are in {location}"
            except:
                return "Couldn't determine location"
        
        elif 'ip address' in lower:
            try:
                response = requests.get('https://api.ipify.org', timeout=3)
                return f"Your IP address is {response.text}"
            except:
                return "Couldn't get IP address"
        
        elif 'translate' in lower:
            text_to_translate = lower.split('translate')[-1].strip()
            try:
                translated = GoogleTranslator(source='auto', target='ne').translate(text_to_translate)
                return f"Translation: {translated}"
            except:
                return "Couldn't translate"
        
        elif 'system info' in lower or 'computer info' in lower:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            return f"CPU: {cpu}%, RAM: {mem}%, Disk: {disk}%"
        
        elif 'empty recycle bin' in lower or 'clear trash' in lower:
            try:
                subprocess.run('rd /s /q %systemdrive%\\$Recycle.bin', shell=True, capture_output=True)
                return "Recycle bin emptied"
            except:
                return "Couldn't empty recycle bin"
        
        elif 'what do you know' in lower or 'tell me about' in lower:
            topic = lower.split('about')[-1].strip() if 'about' in lower else lower.split('know')[-1].strip()
            
            remembered = self.recall(topic)
            if remembered:
                return remembered
            
            self.speak("I don't know that yet. Let me learn it")
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
        
        elif 'stop listening' in lower or 'pause' in lower or 'sleep' in lower:
            self.listening = False
            return f"Going to sleep. Say 'hey Jarvis' to wake me, {self.user_name}"
        
        elif 'stop' in lower or 'exit' in lower or 'quit' in lower:
            return None
        
        return "I'm not sure how to help with that. Can you rephrase?"
    
    def process(self, text):
        if not text:
            return True
        
        english_text = self.translate_to_english(text)
        
        intent = self.detect_intent(english_text)
        
        if intent == 'knowledge':
            key, value = self.extract_knowledge(english_text)
            self.learn(key, value)
            response = "Understood, I've learned that"
        else:
            response = self.execute_action(english_text)
            if response is None:
                self.speak("Shutting down", self.current_language)
                return False
            
            if "not sure" in response.lower() or "rephrase" in response.lower():
                if any(word in english_text.lower() for word in ['what', 'who', 'where', 'when', 'how', 'why']):
                    remembered = self.recall(english_text)
                    if remembered:
                        response = remembered
                    else:
                        self.speak("Let me search that for you")
                        response = self.search_web(english_text)
        
        self.speak(response, self.current_language)
        return True
    
    def continuous_listen(self):
        error_count = 0
        while True:
            try:
                if not self.listening:
                    text = self.listen()
                    if text:
                        lower = text.lower()
                        if 'hey jarvis' in lower or 'हे जार्विस' in lower or 'जार्विस' in lower:
                            self.listening = True
                            self.speak("Yes, I'm here", self.current_language)
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
                        print("[Warning] Multiple failed attempts. Check microphone.")
                        error_count = 0
            except Exception as e:
                print(f"[Error] Listening loop: {e}")
                error_count += 1
                if error_count > 5:
                    self.speak("I'm experiencing technical difficulties")
                    break
    
    def run(self):
        try:
            greeting = f"JARVIS fully operational. All systems online. Ready to assist, {self.user_name}"
            self.speak(greeting)
            print("\n" + "="*70)
            print("जार्विस पूर्ण रूपमा सञ्चालनमा। सबै प्रणाली अनलाइन।")
            print("JARVIS - Advanced Self-Learning AI Assistant with Vision")
            print("Bilingual: English | Nepali (नेपाली)")
            print("Capabilities: Vision & Face Recognition | System Control")
            print("             Web Search | File Management | Weather | News")
            print("             Reminders | Translation | Camera Access | More")
            if VISION_AVAILABLE:
                print("Vision: ✓ Enabled")
            else:
                print("Vision: ✗ Disabled (install opencv-python face-recognition)")
            print("="*70 + "\n")
            self.continuous_listen()
        except KeyboardInterrupt:
            self.speak("Shutting down gracefully")
            print("\n[✓] JARVIS stopped by user")
        except Exception as e:
            print(f"\n[✗] Fatal error: {e}")
            self.speak("Critical error occurred. Shutting down")

if __name__ == "__main__":
    jarvis = Jarvis()
    jarvis.run()
