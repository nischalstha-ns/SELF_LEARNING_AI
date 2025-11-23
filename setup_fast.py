import subprocess
import sys
import os

def install_minimal_requirements():
    """Install only essential packages for fast mode"""
    minimal_packages = [
        'SpeechRecognition',
        'pyttsx3',
        'pyaudio'
    ]
    
    print("Installing minimal requirements for fast mode...")
    for package in minimal_packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✓ {package} installed")
        except:
            print(f"✗ Failed to install {package}")

def create_desktop_shortcut():
    """Create desktop shortcut for ultra fast mode"""
    try:
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        shortcut_path = os.path.join(desktop, 'JARVIS Ultra Fast.bat')
        
        with open(shortcut_path, 'w') as f:
            f.write(f'@echo off\ncd /d "{os.getcwd()}"\npython jarvis_ultra_fast.py\npause')
        
        print(f"✓ Desktop shortcut created: {shortcut_path}")
    except Exception as e:
        print(f"✗ Failed to create shortcut: {e}")

def main():
    print("JARVIS Fast Setup")
    print("=" * 30)
    
    install_minimal_requirements()
    create_desktop_shortcut()
    
    print("\n✓ Fast setup complete!")
    print("Run 'python jarvis_ultra_fast.py' or use the desktop shortcut")

if __name__ == "__main__":
    main()