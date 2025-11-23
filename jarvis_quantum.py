import speech_recognition as sr,pyttsx3,os,threading,ctypes,sys
ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)
e=pyttsx3.init();e.setProperty('rate',500);r=sr.Recognizer();r.energy_threshold=500;r.pause_threshold=0.01
c={'v+':'nircmd changesysvolume 6553','v-':'nircmd changesysvolume -6553','m':'nircmd mutesysvolume 2','c':'start chrome','n':'start notepad','=':'start calc','l':'rundll32 user32.dll,LockWorkStation','s':'nircmd savescreenshot s.png','x':'shutdown /s /t 1','r':'shutdown /r /t 1'}
def s(t):print(t);threading.Thread(target=lambda:(e.say(t),e.runAndWait()),daemon=1).start()
def l():
 try:
  with sr.Microphone()as m:a=r.listen(m,timeout=0.3,phrase_time_limit=1.5);return r.recognize_google(a).lower()
 except:return''
def x(i):
 if'vol'in i and'up'in i:os.system(c['v+']);return'+'
 if'vol'in i and'down'in i:os.system(c['v-']);return'-'
 if'mute'in i:os.system(c['m']);return'M'
 if'chrome'in i:os.system(c['c']);return'C'
 if'note'in i:os.system(c['n']);return'N'
 if'calc'in i:os.system(c['=']);return'='
 if'lock'in i:os.system(c['l']);return'L'
 if'shot'in i:os.system(c['s']);return'S'
 if'shutdown'in i:os.system(c['x']);return'X'
 if'restart'in i:os.system(c['r']);return'R'
 if'time'in i:return __import__('time').strftime('%H:%M')
 if any(w in i for w in['search','what','who']):os.system(f'start https://google.com/search?q={i.split()[-1]}');return'?'
 if'play'in i:os.system(f'start https://youtube.com/results?search_query={i.split()[-1]}');return'P'
 if any(w in i for w in['stop','exit']):return
 return'?'
s('Q');exec('while 1:\n i=l()\n if i:\n  r=x(i)\n  if r is None:break\n  s(r)')