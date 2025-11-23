import keyboard
import threading
import sys
from jarvis import Jarvis

class JarvisBackground:
    def __init__(self):
        self.jarvis = None
        self.active = False
        self.thread = None
        
    def toggle_jarvis(self):
        if not self.active:
            self.start_jarvis()
        else:
            self.stop_jarvis()
    
    def start_jarvis(self):
        if not self.active:
            self.active = True
            print("\n[JARVIS ACTIVATED]")
            self.jarvis = Jarvis()
            self.thread = threading.Thread(target=self.jarvis.run, daemon=True)
            self.thread.start()
    
    def stop_jarvis(self):
        if self.active:
            self.active = False
            print("\n[JARVIS DEACTIVATED]")
            if self.jarvis:
                self.jarvis.listening = False
    
    def run(self):
        print("="*70)
        print("JARVIS Background Service Running")
        print("Press Ctrl+Shift+J to activate/deactivate JARVIS")
        print("Press Ctrl+Shift+Q to quit")
        print("="*70)
        
        keyboard.add_hotkey('ctrl+shift+j', self.toggle_jarvis)
        keyboard.add_hotkey('ctrl+shift+q', lambda: sys.exit(0))
        
        # Auto-start JARVIS
        self.start_jarvis()
        
        keyboard.wait()

if __name__ == "__main__":
    service = JarvisBackground()
    service.run()
