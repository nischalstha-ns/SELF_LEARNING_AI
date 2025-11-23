#!/usr/bin/env python3
import speech_recognition as sr,pyttsx3,os,threading,time
e=pyttsx3.init();e.setProperty('rate',400);r=sr.Recognizer();r.energy_threshold=800;r.pause_threshold=0.02
def s(t):print(t);threading.Thread(target=lambda:(e.say(t),e.runAndWait()),daemon=True).start()
def l():
 try:
  with sr.Microphone()as m:a=r.listen(m,timeout=0.5,phrase_time_limit=2);return r.recognize_google(a).lower()
 except:return""
def x(c):
 if'vol'in c and'up'in c:os.system('nircmd changesysvolume 6553');return"+"
 if'vol'in c and'down'in c:os.system('nircmd changesysvolume -6553');return"-"
 if'mute'in c:os.system('nircmd mutesysvolume 2');return"M"
 if'chrome'in c:os.system('start chrome');return"C"
 if'note'in c:os.system('start notepad');return"N"
 if'calc'in c:os.system('start calc');return"="
 if'time'in c:return time.strftime("%H:%M")
 if any(w in c for w in['search','what','who']):os.system(f'start https://google.com/search?q={c.split()[-1]}');return"S"
 if'play'in c:os.system(f'start https://youtube.com/results?search_query={c.split()[-1]}');return"P"
 if any(w in c for w in['stop','exit']):return None
 return"?"
s("GO")
while True:
 c=l()
 if c:
  r=x(c)
  if r is None:break
  s(r)