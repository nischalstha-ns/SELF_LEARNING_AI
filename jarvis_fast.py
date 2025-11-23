import speech_recognition as sr
import pyttsx3
import subprocess
import os
import json
import threading
import time
from datetime import datetime

class FastJarvis:
    def __init__(self):
        # Core components only
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 200)
        self.engine.setProperty('volume', 1.0)
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 3000
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.5
        
        self.memory = {}
        self.listening = True
        self.user_name = "Sir"
        
        # Lazy imports cache
        self._modules = {}
        
        # Command cache
        self._app_map = {
            'chrome': 'chrome', 'browser': 'chrome', 'notepad': 'notepad',
            'calculator': 'calc', 'paint': 'mspaint', 'explorer': 'explorer',
            'cmd': 'cmd', 'powershell': 'powershell', 'settings': 'ms-settings:'
        }
    
    def _import_module(self, module_name):
        if module_name not in self._modules:
            try:
                if module_name == 'webbrowser':
                    import webbrowser
                    self._modules[module_name] = webbrowser
                elif module_name == 'requests':
                    import requests
                    self._modules[module_name] = requests
                elif module_name == 'pyautogui':
                    import pyautogui
                    self._modules[module_name] = pyautogui
                elif module_name == 'psutil':
                    import psutil
                    self._modules[module_name] = psutil
            except ImportError:
                self._modules[module_name] = None
        return self._modules[module_name]
    
    def speak(self, text):
        print(f"JARVIS: {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            pass
    
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
    
    def execute_command(self, command):
        # System controls
        if 'volume up' in command:
            subprocess.run('nircmd changesysvolume 6553', shell=True)
            return "Volume up"
        elif 'volume down' in command:
            subprocess.run('nircmd changesysvolume -6553', shell=True)
            return "Volume down"
        elif 'mute' in command:
            subprocess.run('nircmd mutesysvolume 2', shell=True)
            return "Muted"
        
        # App controls
        elif 'open' in command:
            app = command.split('open')[-1].strip()
            app_exe = self._app_map.get(app, app)
            subprocess.Popen(app_exe, shell=True)
            return f"Opening {app}"
        
        elif 'close' in command:
            app = command.split('close')[-1].strip()
            subprocess.run(f'taskkill /IM {app}.exe /F', shell=True, capture_output=True)
            return f"Closing {app}"
        
        # Quick searches
        elif 'search' in command or any(w in command for w in ['what', 'who', 'where']):
            query = command.replace('search', '').replace('what is', '').replace('who is', '').strip()
            webbrowser = self._import_module('webbrowser')
            if webbrowser:
                webbrowser.open(f'https://www.google.com/search?q={query}')
                return f"Searching {query}"
        
        elif 'play' in command:
            query = command.split('play')[-1].strip()
            webbrowser = self._import_module('webbrowser')
            if webbrowser:
                webbrowser.open(f'https://www.youtube.com/results?search_query={query}')
                return f"Playing {query}"
        
        # Time/Date
        elif 'time' in command:
            return datetime.now().strftime("It's %I:%M %p")
        elif 'date' in command:
            return datetime.now().strftime("Today is %A, %B %d")
        
        # System info
        elif 'battery' in command:
            psutil = self._import_module('psutil')
            if psutil:
                battery = psutil.sensors_battery()
                if battery:
                    return f"Battery at {battery.percent}%"
        
        elif 'cpu' in command:
            psutil = self._import_module('psutil')
            if psutil:
                return f"CPU usage {psutil.cpu_percent()}%"
        
        # Screenshot
        elif 'screenshot' in command:
            pyautogui = self._import_module('pyautogui')
            if pyautogui:
                pyautogui.screenshot().save(f'screenshot_{int(time.time())}.png')
                return "Screenshot taken"
        
        # System actions
        elif 'lock' in command:
            subprocess.run('rundll32.exe user32.dll,LockWorkStation', shell=True)
            return "Locking"
        elif 'shutdown' in command:
            subprocess.run('shutdown /s /t 5', shell=True)
            return "Shutting down"
        elif 'restart' in command:
            subprocess.run('shutdown /r /t 5', shell=True)
            return "Restarting"
        
        # Exit commands
        elif any(w in command for w in ['stop', 'exit', 'quit']):
            return None
        
        return "Command not recognized"
    
    def run(self):
        self.speak("JARVIS Fast Mode Ready")
        print("\n" + "="*50)
        print("JARVIS FAST MODE - Optimized Performance")
        print("Say 'stop' or 'exit' to quit")
        print("="*50 + "\n")
        
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
    jarvis = FastJarvis()
    jarvis.run()