import os
import subprocess
import sys

def show_menu():
    print("\n" + "="*60)
    print("           JARVIS - AI Assistant Launcher")
    print("="*60)
    print("Choose your performance mode:")
    print()
    print("1. SINGULARITY Mode  - Beyond optimization limits")
    print("2. PHOTON Mode       - Light-speed execution")
    print("3. ATOMIC Mode       - Molecular-level efficiency")
    print("4. NANO Mode         - Microscopic overhead")
    print("5. QUANTUM Mode      - Quantum-level performance")
    print("6. ULTIMATE Mode     - 100% optimized")
    print("7. TURBO Mode        - Pre-compiled")
    print("8. MAX Mode          - Minimal code")
    print("9. INSTANT Mode      - Zero-delay")
    print("A. Ultra Fast Mode   - Original optimized")
    print("B. Fast Mode         - Balanced")
    print("C. Advanced Mode     - Full features + optimized + secure")
    print("D. Full Mode         - Complete features")
    print("E. Background Mode   - Service with hotkeys")
    print("F. Performance Test  - Compare all modes")
    print("0. Exit")
    print("="*60)

def launch_mode(choice):
    scripts = {
        '1': 'jarvis_singularity.py',
        '2': 'jarvis_photon.py',
        '3': 'jarvis_atomic.py',
        '4': 'jarvis_nano.py',
        '5': 'jarvis_quantum.py',
        '6': 'jarvis_ultimate.py',
        '7': 'jarvis_turbo.py',
        '8': 'jarvis_max.py',
        '9': 'jarvis_instant.py',
        'a': 'jarvis_ultra_fast.py',
        'b': 'jarvis_fast.py',
        'c': 'jarvis_advanced.py',
        'd': 'jarvis.py',
        'e': 'jarvis_background.py',
        'f': 'performance_test.py'
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
        choice = input("\nEnter your choice (0-9, A-F): ").strip().lower()
        
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