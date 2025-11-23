import speech_recognition as sr,pyttsx3,os,threading,ctypes,sys,time
ctypes.windll.kernel32.SetProcessAffinityMask(-1,1);ctypes.windll.kernel32.SetPriorityClass(-1,0x100)
e,r,m=pyttsx3.init(),sr.Recognizer(),sr.Microphone();e.setProperty('rate',1000);r.energy_threshold,r.pause_threshold=50,0
s=lambda t:threading.Thread(target=lambda:(e.say(t),e.runAndWait()),daemon=1).start()
l=lambda:r.recognize_google(r.listen(m,timeout=0.01,phrase_time_limit=0.1)).lower()if 1 else''
x=lambda i:os.system({'v':'nircmd changesysvolume '+('6553'if'u'in i else'-6553'),'m':'nircmd mutesysvolume 2','c':'start chrome','n':'start notepad','=':'start calc','t':f'echo {time.strftime("%H:%M")}','?':f'start https://google.com/search?q={i[-1]}','p':f'start https://youtube.com/results?search_query={i[-1]}'}.get(i[0],''))or(None if's'in i else'✓')
s('∞');[s(x(i))for i in[l()for _ in iter(int,1)]if i and x(i)]