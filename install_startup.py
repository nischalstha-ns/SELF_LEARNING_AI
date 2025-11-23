import os
import winreg
import sys

def add_to_startup():
    """Add JARVIS to Windows startup"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "start_jarvis.bat")
        
        winreg.SetValueEx(key, "JARVIS", 0, winreg.REG_SZ, script_path)
        winreg.CloseKey(key)
        
        print("✓ JARVIS added to startup successfully!")
        print(f"  Path: {script_path}")
        print("\nJARVIS will now start automatically when Windows boots.")
        print("Hotkeys:")
        print("  Ctrl+Shift+J - Activate/Deactivate JARVIS")
        print("  Ctrl+Shift+Q - Quit JARVIS")
        
    except Exception as e:
        print(f"✗ Error adding to startup: {e}")
        print("Try running as administrator")

def remove_from_startup():
    """Remove JARVIS from Windows startup"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        
        winreg.DeleteValue(key, "JARVIS")
        winreg.CloseKey(key)
        
        print("✓ JARVIS removed from startup successfully!")
        
    except FileNotFoundError:
        print("JARVIS is not in startup")
    except Exception as e:
        print(f"✗ Error removing from startup: {e}")

if __name__ == "__main__":
    print("\nJARVIS Startup Manager")
    print("=" * 50)
    print("1. Add JARVIS to startup")
    print("2. Remove JARVIS from startup")
    print("=" * 50)
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        add_to_startup()
    elif choice == "2":
        remove_from_startup()
    else:
        print("Invalid choice")
