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
import ast
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

try:
    import wikipedia
    import pyjokes
    import pyperclip
    from vision_module import VisionModule
    VISION_AVAILABLE = True
except:
    VISION_AVAILABLE = False

class AdvancedJarvis:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 200)
        self.engine.setProperty('volume', 1.0)
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 3000
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.5
        
        self.memory_file = 'memory.json'
        self.memory = self.load_memory()
        self.listening = True
        self.user_name = self.memory.get('user_name', 'Sir')
        
        if VISION_AVAILABLE:
            self.vision = VisionModule()
        
        self.command_cache = {}
        self.web_cache = {}
        
    def speak(self, text):
        print(f"JARVIS: {text}")
        threading.Thread(target=lambda: (self.engine.say(text), self.engine.runAndWait()), daemon=True).start()
    
    def listen(self):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=8)
            text = self.recognizer.recognize_google(audio, language='en-US')
            print(f"You: {text}")
            return text.lower()
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
    
    def safe_calculate(self, expr):
        try:
            expr = expr.replace('plus', '+').replace('minus', '-').replace('times', '*').replace('multiply', '*')
            expr = expr.replace('divided by', '/').replace('divide', '/').replace('power', '**')
            expr = expr.replace('x', '*').replace('÷', '/')
            node = ast.parse(expr, mode='eval')
            for n in ast.walk(node):
                if isinstance(n, (ast.Call, ast.Import, ast.ImportFrom)):
                    raise ValueError("Invalid expression")
            return eval(compile(node, '<string>', 'eval'), {"__builtins__": {}}, {})
        except:
            return None
    
    def search_web(self, query):
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if cache_key in self.web_cache:
            return self.web_cache[cache_key]
        
        try:
            result = wikipedia.summary(query, sentences=2, auto_suggest=True)
            if result and len(result) > 20:
                self.web_cache[cache_key] = result
                self.learn(query, result)
                return result
        except:
            pass
        
        try:
            url = f"https://api.duckduckgo.com/?q={query}&format=json"
            response = requests.get(url, timeout=3)
            data = response.json()
            if data.get('AbstractText'):
                answer = data['AbstractText']
                self.web_cache[cache_key] = answer
                self.learn(query, answer)
                return answer
        except:
            pass
        
        webbrowser.open(f'https://www.google.com/search?q={query}')
        return f"Opened browser search for {query}"
    
    def learn(self, key, value):
        self.memory[key.lower()] = value
        self.save_memory()
    
    def recall(self, query):
        query_lower = query.lower()
        if query_lower in self.memory:
            return self.memory[query_lower]
        for key in self.memory:
            if query_lower in key or key in query_lower:
                return self.memory[key]
        return None
    
    def vision_command(self, command):
        if not VISION_AVAILABLE:
            return "Vision features not available. Install opencv-python and face-recognition"
        
        if 'who am i seeing' in command or 'who do you see' in command:
            return self.vision.who_am_i_seeing()
        
        elif 'learn my face' in command or 'remember my face' in command:
            name = self.user_name
            if self.vision.learn_face(name):
                return f"I've learned your face, {name}"
            return "Couldn't detect a face. Please look at the camera"
        
        elif 'learn face' in command:
            name = command.split('face')[-1].strip()
            if self.vision.learn_face(name):
                return f"I've learned {name}'s face"
            return "Couldn't detect a face"
        
        elif 'take photo' in command or 'take picture' in command:
            filename = self.vision.take_photo()
            if filename:
                return f"Photo saved as {filename}"
            return "Camera not available"
        
        elif 'show camera' in command or 'open camera' in command:
            self.vision.show_camera_feed(duration=10)
            return "Camera feed closed"
        
        elif 'describe scene' in command or 'what do you see' in command:
            return self.vision.describe_scene()
        
        elif 'stop camera' in command:
            self.vision.stop_camera()
            return "Camera stopped"
        
        return None
    
    def system_control(self, command):
        if 'volume up' in command:
            pyautogui.press('volumeup', presses=5)
            return "Volume increased"
        elif 'volume down' in command:
            pyautogui.press('volumedown', presses=5)
            return "Volume decreased"
        elif 'mute' in command:
            pyautogui.press('volumemute')
            return "Volume toggled"
        
        elif 'brightness up' in command:
            subprocess.run('powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,100)', shell=True, capture_output=True)
            return "Brightness increased"
        elif 'brightness down' in command:
            subprocess.run('powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,30)', shell=True, capture_output=True)
            return "Brightness decreased"
        
        elif 'wifi off' in command:
            subprocess.run('netsh interface set interface "Wi-Fi" disabled', shell=True, capture_output=True)
            return "WiFi disabled"
        elif 'wifi on' in command:
            subprocess.run('netsh interface set interface "Wi-Fi" enabled', shell=True, capture_output=True)
            return "WiFi enabled"
        
        elif 'screenshot' in command:
            screenshot = pyautogui.screenshot()
            filename = f'screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            screenshot.save(filename)
            return f"Screenshot saved as {filename}"
        
        elif 'lock' in command:
            subprocess.run('rundll32.exe user32.dll,LockWorkStation', shell=True)
            return "Locking computer"
        
        elif 'shutdown' in command:
            subprocess.run('shutdown /s /t 5', shell=True)
            return "Shutting down in 5 seconds"
        
        elif 'restart' in command:
            subprocess.run('shutdown /r /t 5', shell=True)
            return "Restarting in 5 seconds"
        
        elif 'cancel shutdown' in command:
            subprocess.run('shutdown /a', shell=True)
            return "Shutdown cancelled"
        
        elif 'battery' in command:
            battery = psutil.sensors_battery()
            if battery:
                return f"Battery at {battery.percent}%, {'charging' if battery.power_plugged else 'not charging'}"
            return "Battery info not available"
        
        elif 'cpu' in command:
            cpu = psutil.cpu_percent(interval=1)
            return f"CPU usage is {cpu}%"
        
        elif 'memory' in command or 'ram' in command:
            mem = psutil.virtual_memory()
            return f"Memory usage is {mem.percent}%, {mem.available // (1024**3)} GB available"
        
        return None
    
    def execute_command(self, command):
        vision_response = self.vision_command(command)
        if vision_response:
            return vision_response
        
        sys_response = self.system_control(command)
        if sys_response:
            return sys_response
        
        if 'open' in command:
            app = command.split('open')[-1].strip()
            app_map = {
                'chrome': 'chrome', 'browser': 'chrome', 'notepad': 'notepad',
                'calculator': 'calc', 'paint': 'mspaint', 'explorer': 'explorer',
                'cmd': 'cmd', 'powershell': 'powershell', 'settings': 'ms-settings:'
            }
            app_to_open = app_map.get(app, app)
            subprocess.Popen(app_to_open, shell=True)
            return f"Opening {app}"
        
        elif 'close' in command:
            app = command.split('close')[-1].strip()
            subprocess.run(f'taskkill /IM {app}.exe /F', shell=True, capture_output=True)
            return f"Closing {app}"
        
        elif 'search' in command or any(w in command for w in ['what', 'who', 'where', 'when', 'how', 'why']):
            query = command.replace('search', '').replace('what is', '').replace('who is', '').strip()
            remembered = self.recall(query)
            if remembered:
                return f"I remember: {remembered}"
            return self.search_web(query)
        
        elif 'play' in command:
            query = command.split('play')[-1].strip()
            webbrowser.open(f'https://www.youtube.com/results?search_query={query}')
            return f"Playing {query}"
        
        elif 'time' in command:
            return datetime.now().strftime("It's %I:%M %p")
        
        elif 'date' in command:
            return datetime.now().strftime("Today is %A, %B %d, %Y")
        
        elif 'calculate' in command:
            expr = command.replace('calculate', '').replace('what is', '').strip()
            result = self.safe_calculate(expr)
            if result is not None:
                return f"The answer is {result}"
            return "I couldn't calculate that"
        
        elif 'joke' in command:
            try:
                return pyjokes.get_joke()
            except:
                return "Why do programmers prefer dark mode? Because light attracts bugs!"
        
        elif 'weather' in command:
            city = command.split('in')[-1].strip() if 'in' in command else self.memory.get('user_location', 'Kathmandu')
            try:
                url = f"https://wttr.in/{city}?format=%C+%t+%w"
                response = requests.get(url, timeout=3)
                return f"Weather in {city}: {response.text}"
            except:
                return "Couldn't fetch weather"
        
        elif 'location' in command or 'where am i' in command:
            try:
                response = requests.get('https://ipapi.co/json/', timeout=3)
                data = response.json()
                location = f"{data.get('city', 'Unknown')}, {data.get('country_name', 'Unknown')}"
                self.memory['user_location'] = data.get('city', 'Unknown')
                self.save_memory()
                return f"You are in {location}"
            except:
                return "Couldn't determine location"
        
        elif any(w in command for w in ['stop', 'exit', 'quit']):
            return None
        
        return "I'm not sure how to help with that"
    
    def run(self):
        self.speak(f"JARVIS Advanced Mode Ready. All systems online, {self.user_name}")
        print("\n" + "="*70)
        print("JARVIS ADVANCED - Full Features + Optimized Performance")
        if VISION_AVAILABLE:
            print("Vision: ✓ Enabled")
        print("="*70 + "\n")
        
        while True:
            try:
                command = self.listen()
                if command:
                    response = self.execute_command(command)
                    if response is None:
                        self.speak("Goodbye")
                        break
                    self.speak(response)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    AdvancedJarvis().run()