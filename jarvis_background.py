import keyboard
import threading
import sys
import time
import pyttsx3
from jarvis import Jarvis

class JarvisBackground:
    def __init__(self):
        self.jarvis = None
        self.active = False
        self.thread = None
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 190)
        
    def speak_quick(self, text):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            pass
    
    def toggle_jarvis(self):
        if not self.active:
            self.start_jarvis()
        else:
            self.stop_jarvis()
    
    def start_jarvis(self):
        if not self.active:
            self.active = True
            print("\n" + "="*70)
            print("[✓] JARVIS ACTIVATED")
            print("="*70)
            self.speak_quick("JARVIS activated")
            try:
                self.jarvis = Jarvis()
                self.thread = threading.Thread(target=self.jarvis.run, daemon=True)
                self.thread.start()
            except Exception as e:
                print(f"[✗] Error starting JARVIS: {e}")
                self.active = False
    
    def stop_jarvis(self):
        if self.active:
            self.active = False
            print("\n" + "="*70)
            print("[✓] JARVIS DEACTIVATED")
            print("="*70)
            self.speak_quick("JARVIS deactivated")
            if self.jarvis:
                self.jarvis.listening = False
    
    def quit_jarvis(self):
        print("\n[✓] JARVIS shutting down...")
        self.speak_quick("Goodbye")
        time.sleep(1)
        sys.exit(0)
    
    def run(self):
        print("\n" + "="*70)
        print("     JARVIS - Advanced AI Assistant Background Service")
        print("="*70)
        print("  Status: Running in background")
        print("  Hotkeys:")
        print("    • Ctrl+Shift+J  →  Activate/Deactivate JARVIS")
        print("    • Ctrl+Shift+Q  →  Quit JARVIS")
        print("="*70 + "\n")
        
        keyboard.add_hotkey('ctrl+shift+j', self.toggle_jarvis)
        keyboard.add_hotkey('ctrl+shift+q', self.quit_jarvis)
        
        # Auto-start JARVIS
        self.start_jarvis()
        
        keyboard.wait()

if __name__ == "__main__":
    try:
        service = JarvisBackground()
        service.run()
    except KeyboardInterrupt:
        print("\n[✓] JARVIS stopped by user")
    except Exception as e:
        print(f"\n[✗] Fatal error: {e}")
        input("Press Enter to exit...")
