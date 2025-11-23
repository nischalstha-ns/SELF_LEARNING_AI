import os
import subprocess
import sys

def show_menu():
    print("\n" + "="*60)
    print("           JARVIS - AI Assistant Launcher")
    print("="*60)
    print("Choose your performance mode:")
    print()
    print("1. Ultra Fast Mode    - Maximum speed, core commands")
    print("2. Fast Mode         - Balanced performance & features")
    print("3. Full Mode         - Complete feature set")
    print("4. Background Mode   - Service with hotkeys")
    print("5. Performance Test  - Compare all modes")
    print("6. Setup Fast Mode   - Install minimal requirements")
    print("0. Exit")
    print("="*60)

def launch_mode(choice):
    scripts = {
        '1': 'jarvis_ultra_fast.py',
        '2': 'jarvis_fast.py', 
        '3': 'jarvis.py',
        '4': 'jarvis_background.py',
        '5': 'performance_test.py',
        '6': 'setup_fast.py'
    }
    
    if choice in scripts:
        script = scripts[choice]
        if os.path.exists(script):
            print(f"\nLaunching {script}...")
            subprocess.run([sys.executable, script])
        else:
            print(f"Error: {script} not found!")
    elif choice == '0':
        print("Goodbye!")
        return False
    else:
        print("Invalid choice!")
    
    return True

def main():
    while True:
        show_menu()
        choice = input("\nEnter your choice (0-6): ").strip()
        
        if not launch_mode(choice):
            break
        
        input("\nPress Enter to return to menu...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"\nError: {e}")
        input("Press Enter to exit...")