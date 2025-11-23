import speech_recognition as sr
import pyttsx3
import os
import threading
import time

# Pre-compile everything for zero-delay execution
ENGINE = pyttsx3.init()
ENGINE.setProperty('rate', 350)
REC = sr.Recognizer()
REC.energy_threshold = 1000
REC.pause_threshold = 0.05

COMMANDS = {
    'volume up': 'nircmd changesysvolume 6553',
    'volume down': 'nircmd changesysvolume -6553', 
    'mute': 'nircmd mutesysvolume 2',
    'chrome': 'start chrome',
    'notepad': 'start notepad',
    'calculator': 'start calc'
}

def speak(text):
    print(text)
    threading.Thread(target=lambda: (ENGINE.say(text), ENGINE.runAndWait()), daemon=True).start()

def listen():
    try:
        with sr.Microphone() as mic:
            audio = REC.listen(mic, timeout=0.8, phrase_time_limit=2.5)
        return REC.recognize_google(audio).lower()
    except:
        return ""

def execute(cmd):
    # Ultra-fast command matching
    for key, value in COMMANDS.items():
        if key.replace(' ', '') in cmd.replace(' ', ''):
            os.system(value)
            return key.split()[0].upper()
    
    if 'time' in cmd:
        return time.strftime("%H:%M")
    if any(w in cmd for w in ['search', 'what', 'who']):
        os.system(f'start https://google.com/search?q={cmd.split()[-1]}')
        return "SEARCH"
    if 'play' in cmd:
        os.system(f'start https://youtube.com/results?search_query={cmd.split()[-1]}')
        return "PLAY"
    if any(w in cmd for w in ['stop', 'exit', 'quit']):
        return None
    return "UNKNOWN"

def main():
    speak("TURBO READY")
    while True:
        command = listen()
        if command:
            result = execute(command)
            if result is None:
                speak("BYE")
                break
            speak(result)

if __name__ == "__main__":
    main()