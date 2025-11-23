import speech_recognition as sr
import pyttsx3
import subprocess
import os
import threading
from datetime import datetime

class MaxJarvis:
    def __init__(self):
        # Ultra-minimal init
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 250)
        
        self.r = sr.Recognizer()
        self.r.energy_threshold = 2000
        self.r.dynamic_energy_threshold = False
        self.r.pause_threshold = 0.2
        
        # Pre-cached commands for zero-delay execution
        self.cmds = {
            'vol up': 'nircmd changesysvolume 6553',
            'vol down': 'nircmd changesysvolume -6553',
            'mute': 'nircmd mutesysvolume 2',
            'chrome': 'start chrome',
            'notepad': 'start notepad',
            'calc': 'start calc',
            'lock': 'rundll32 user32.dll,LockWorkStation',
            'shot': 'nircmd savescreenshot screen.png',
            'shutdown': 'shutdown /s /t 1',
            'restart': 'shutdown /r /t 1'
        }
    
    def speak(self, text):
        print(f"J: {text}")
        threading.Thread(target=lambda: (self.engine.say(text), self.engine.runAndWait()), daemon=True).start()
    
    def listen(self):
        try:
            with sr.Microphone() as src:
                audio = self.r.listen(src, timeout=1.5, phrase_time_limit=4)
            return self.r.recognize_google(audio).lower()
        except:
            return ""
    
    def exec(self, cmd):
        # Direct string matching for instant execution
        if 'vol up' in cmd or 'volume up' in cmd:
            os.system(self.cmds['vol up'])
            return "Vol up"
        if 'vol down' in cmd or 'volume down' in cmd:
            os.system(self.cmds['vol down'])
            return "Vol down"
        if 'mute' in cmd:
            os.system(self.cmds['mute'])
            return "Muted"
        if 'chrome' in cmd:
            os.system(self.cmds['chrome'])
            return "Chrome"
        if 'notepad' in cmd:
            os.system(self.cmds['notepad'])
            return "Notepad"
        if 'calc' in cmd:
            os.system(self.cmds['calc'])
            return "Calc"
        if 'lock' in cmd:
            os.system(self.cmds['lock'])
            return "Locked"
        if 'shot' in cmd or 'screenshot' in cmd:
            os.system(self.cmds['shot'])
            return "Shot"
        if 'shutdown' in cmd:
            os.system(self.cmds['shutdown'])
            return "Bye"
        if 'restart' in cmd:
            os.system(self.cmds['restart'])
            return "Restart"
        if 'time' in cmd:
            return datetime.now().strftime("%H:%M")
        if 'search' in cmd or 'what' in cmd or 'who' in cmd:
            q = cmd.split()[-1]
            os.system(f'start https://google.com/search?q={q}')
            return f"Search {q}"
        if 'play' in cmd:
            q = cmd.split()[-1]
            os.system(f'start https://youtube.com/results?search_query={q}')
            return f"Play {q}"
        if 'stop' in cmd or 'exit' in cmd:
            return None
        return "?"
    
    def run(self):
        self.speak("Max ready")
        while True:
            cmd = self.listen()
            if cmd:
                res = self.exec(cmd)
                if res is None:
                    break
                self.speak(res)

if __name__ == "__main__":
    MaxJarvis().run()