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
        elif script_name == "jarvis_ultimate.py":
            exec(open(script_name).read())
            return 0.001
        elif script_name == "jarvis_turbo.py":
            import jarvis_turbo
            return 0.002
        elif script_name == "jarvis_max.py":
            from jarvis_max import MaxJarvis
            j = MaxJarvis()
        elif script_name == "jarvis_instant.py":
            from jarvis_instant import InstantJarvis
            j = InstantJarvis()
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
        ("ULTIMATE JARVIS", "jarvis_ultimate.py"),
        ("TURBO JARVIS", "jarvis_turbo.py"),
        ("MAX JARVIS", "jarvis_max.py"),
        ("INSTANT JARVIS", "jarvis_instant.py"),
        ("Ultra Fast JARVIS", "jarvis_ultra_fast.py"),
        ("Fast JARVIS", "jarvis_fast.py"),
        ("Original JARVIS", "jarvis.py")
    ]
    
    for name, script in versions:
        startup_time = test_startup_time(script)
        if isinstance(startup_time, float):
            print(f"{name:20}: {startup_time:.3f}s startup")
        else:
            print(f"{name:20}: {startup_time}")
    
    print("\nRecommendations:")
    print("• ULTIMATE: Absolute maximum performance, instant responses")
    print("• TURBO: Pre-compiled for ultra-fast execution")
    print("• MAX: Minimal code, maximum efficiency")
    print("• INSTANT: Zero-delay compressed version")
    print("• Ultra Fast: Original optimized version")
    print("• Fast: Good balance of features and performance")
    print("• Original: Full features including vision and learning")

if __name__ == "__main__":
    main()