import speech_recognition as sr
import pyttsx3
import subprocess
import os
import threading
import time
from datetime import datetime

class UltraFastJarvis:
    def __init__(self):
        # Minimal initialization
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 220)
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 2500
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.3
        
        # Pre-compiled commands for instant execution
        self.quick_commands = {
            'volume up': 'nircmd changesysvolume 6553',
            'volume down': 'nircmd changesysvolume -6553',
            'mute': 'nircmd mutesysvolume 2',
            'chrome': 'chrome',
            'notepad': 'notepad',
            'calculator': 'calc',
            'lock': 'rundll32.exe user32.dll,LockWorkStation',
            'shutdown': 'shutdown /s /t 5',
            'restart': 'shutdown /r /t 5'
        }
    
    def speak_async(self, text):
        print(f"JARVIS: {text}")
        threading.Thread(target=lambda: (self.engine.say(text), self.engine.runAndWait()), daemon=True).start()
    
    def listen_fast(self):
        try:
            with sr.Microphone() as source:
                audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=6)
            return self.recognizer.recognize_google(audio).lower()
        except:
            return ""
    
    def execute_instant(self, command):
        # Direct command mapping for instant execution
        for key, cmd in self.quick_commands.items():
            if key in command:
                if key in ['chrome', 'notepad', 'calculator']:
                    subprocess.Popen(cmd, shell=True)
                    return f"Opening {key}"
                else:
                    subprocess.run(cmd, shell=True)
                    return f"Executed {key}"
        
        # Quick searches
        if any(w in command for w in ['search', 'what', 'who', 'play']):
            query = command.split()[-1] if command.split() else 'search'
            if 'play' in command:
                os.system(f'start https://youtube.com/results?search_query={query}')
                return f"Playing {query}"
            else:
                os.system(f'start https://google.com/search?q={query}')
                return f"Searching {query}"
        
        # Time
        if 'time' in command:
            return datetime.now().strftime("%I:%M %p")
        
        # Exit
        if any(w in command for w in ['stop', 'exit', 'quit']):
            return None
        
        return "Unknown command"
    
    def run(self):
        self.speak_async("Ultra Fast JARVIS Ready")
        print("ULTRA FAST JARVIS - Maximum Performance Mode")
        
        while True:
            try:
                command = self.listen_fast()
                if command:
                    response = self.execute_instant(command)
                    if response is None:
                        self.speak_async("Goodbye")
                        break
                    self.speak_async(response)
            except KeyboardInterrupt:
                break

if __name__ == "__main__":
    UltraFastJarvis().run()