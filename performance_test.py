import time
import subprocess
import sys

def test_startup_time(script_name):
    """Test how fast each version starts up"""
    start_time = time.time()
    try:
        # Just import and initialize, don't run
        if script_name == "jarvis.py":
            from jarvis import Jarvis
            j = Jarvis()
        elif script_name == "jarvis_fast.py":
            from jarvis_fast import FastJarvis
            j = FastJarvis()
        elif script_name == "jarvis_ultra_fast.py":
            from jarvis_ultra_fast import UltraFastJarvis
            j = UltraFastJarvis()
        
        end_time = time.time()
        return end_time - start_time
    except Exception as e:
        return f"Error: {e}"

def main():
    print("JARVIS Performance Comparison")
    print("=" * 50)
    
    versions = [
        ("Original JARVIS", "jarvis.py"),
        ("Fast JARVIS", "jarvis_fast.py"),
        ("Ultra Fast JARVIS", "jarvis_ultra_fast.py")
    ]
    
    for name, script in versions:
        startup_time = test_startup_time(script)
        if isinstance(startup_time, float):
            print(f"{name:20}: {startup_time:.3f}s startup")
        else:
            print(f"{name:20}: {startup_time}")
    
    print("\nRecommendations:")
    print("• Ultra Fast: Best for quick commands and maximum speed")
    print("• Fast: Good balance of features and performance")
    print("• Original: Full features including vision and learning")

if __name__ == "__main__":
    main()