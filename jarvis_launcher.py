import os
import subprocess
import sys

def show_menu():
    print("\n" + "="*60)
    print("           JARVIS - AI Assistant Launcher")
    print("="*60)
    print("Choose your performance mode:")
    print()
    print("1. ULTIMATE Mode     - 100% optimized, instant response")
    print("2. TURBO Mode        - Pre-compiled, ultra-fast")
    print("3. MAX Mode          - Minimal code, maximum speed")
    print("4. INSTANT Mode      - Compressed, zero-delay")
    print("5. Ultra Fast Mode   - Original optimized version")
    print("6. Fast Mode         - Balanced performance")
    print("7. Full Mode         - Complete feature set")
    print("8. Background Mode   - Service with hotkeys")
    print("9. Performance Test  - Compare all modes")
    print("0. Exit")
    print("="*60)

def launch_mode(choice):
    scripts = {
        '1': 'jarvis_ultimate.py',
        '2': 'jarvis_turbo.py',
        '3': 'jarvis_max.py',
        '4': 'jarvis_instant.py',
        '5': 'jarvis_ultra_fast.py',
        '6': 'jarvis_fast.py',
        '7': 'jarvis.py',
        '8': 'jarvis_background.py',
        '9': 'performance_test.py'
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
        choice = input("\nEnter your choice (0-9): ").strip()
        
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