import speech_recognition as sr,pyttsx3,os,threading
e,r=pyttsx3.init(),sr.Recognizer();e.setProperty('rate',600);r.energy_threshold,r.pause_threshold=300,0.005
def s(t):threading.Thread(target=lambda:(e.say(t),e.runAndWait()),daemon=1).start()
def l():
 try:return r.recognize_google(r.listen(sr.Microphone(),timeout=0.2,phrase_time_limit=1)).lower()
 except:return''
def x(i):
 exec({'vol up':'os.system("nircmd changesysvolume 6553")','vol down':'os.system("nircmd changesysvolume -6553")','mute':'os.system("nircmd mutesysvolume 2")','chrome':'os.system("start chrome")','notepad':'os.system("start notepad")','calc':'os.system("start calc")','time':'return __import__("time").strftime("%H:%M")','search':'os.system(f"start https://google.com/search?q={i.split()[-1]}")','play':'os.system(f"start https://youtube.com/results?search_query={i.split()[-1]}")','stop':'return None'}.get(next((k for k in['vol up','vol down','mute','chrome','notepad','calc','time','search','play','stop']if k in i),''),'return "?"'))
s('N')
while 1:
 i=l()
 if i:
  r=x(i)
  if r is None:break
  if r:s(r)