import speech_recognition as sr
import pyttsx3
import os
import threading

class InstantJarvis:
    def __init__(self):
        self.e = pyttsx3.init()
        self.e.setProperty('rate', 300)
        self.r = sr.Recognizer()
        self.r.energy_threshold = 1500
        self.r.pause_threshold = 0.1
        
    def s(self, t):
        print(t)
        threading.Thread(target=lambda: (self.e.say(t), self.e.runAndWait()), daemon=True).start()
    
    def l(self):
        try:
            with sr.Microphone() as m:
                a = self.r.listen(m, timeout=1, phrase_time_limit=3)
            return self.r.recognize_google(a).lower()
        except:
            return ""
    
    def x(self, c):
        if 'vol' in c and 'up' in c: os.system('nircmd changesysvolume 6553'); return "+"
        if 'vol' in c and 'down' in c: os.system('nircmd changesysvolume -6553'); return "-"
        if 'mute' in c: os.system('nircmd mutesysvolume 2'); return "M"
        if 'chrome' in c: os.system('start chrome'); return "C"
        if 'note' in c: os.system('start notepad'); return "N"
        if 'calc' in c: os.system('start calc'); return "="
        if 'lock' in c: os.system('rundll32 user32.dll,LockWorkStation'); return "L"
        if 'time' in c: return __import__('datetime').datetime.now().strftime("%H:%M")
        if any(w in c for w in ['search','what','who']): q=c.split()[-1]; os.system(f'start https://google.com/search?q={q}'); return "S"
        if 'play' in c: q=c.split()[-1]; os.system(f'start https://youtube.com/results?search_query={q}'); return "P"
        if any(w in c for w in ['stop','exit']): return None
        return "?"
    
    def run(self):
        self.s("Ready")
        while True:
            c = self.l()
            if c:
                r = self.x(c)
                if r is None: break
                self.s(r)

if __name__ == "__main__":
    InstantJarvis().run()