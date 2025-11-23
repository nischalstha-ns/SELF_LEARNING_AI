import speech_recognition as sr,pyttsx3,os,threading,multiprocessing
multiprocessing.set_start_method('spawn',force=True)
e,r=pyttsx3.init(),sr.Recognizer();e.setProperty('rate',700);r.energy_threshold,r.pause_threshold=200,0.001
m=sr.Microphone()
def s(t):threading.Thread(target=lambda:(e.say(t),e.runAndWait()),daemon=1).start()
def l():
 try:return r.recognize_google(r.listen(m,timeout=0.1,phrase_time_limit=0.8)).lower()
 except:return''
c=lambda i:os.system({'vol up':'nircmd changesysvolume 6553','vol down':'nircmd changesysvolume -6553','mute':'nircmd mutesysvolume 2','chrome':'start chrome','notepad':'start notepad','calc':'start calc','lock':'rundll32 user32.dll,LockWorkStation','shot':'nircmd savescreenshot a.png'}.get(next((k for k in['vol up','vol down','mute','chrome','notepad','calc','lock','shot']if k in i),''))or f'start https://{"youtube.com/results?search_query="if"play"in i else"google.com/search?q="}{i.split()[-1]}')if any(w in i for w in['vol','mute','chrome','notepad','calc','lock','shot','search','play','what','who'])else None
s('A')
[s('✓')if c(i)is None else None for i in iter(l,'')if i and(c(i)or i in['stop','exit'])]