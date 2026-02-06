import os
import sys
import subprocess
import datetime
import time

def log_pulse(message):
    """Simple logger that prints to console immediately."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def get_venv_python():
    """Explicitly looks for the project virtual environment."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # The path specifically for your D:\GitHub\VolatilityHunter setup
    venv_path = os.path.join(base_dir, "venv", "Scripts", "python.exe")
    
    if os.path.exists(venv_path):
        return venv_path
    
    log_pulse(f"[WARNING] Venv not found at {venv_path}")
    return sys.executable

def main():
    log_pulse("--- SCHEDULER REPAIR V3.0 (MANUAL FORCE) ---")
    
    # 1. Anchor to directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    log_pulse(f"Working Directory: {current_dir}")
    
    # 2. Find VENV
    python_exe = get_venv_python()
    log_pulse(f"STEP 2: Selected Interpreter: {python_exe}")
    
    # 3. Set automation environment to prevent any blocking calls
    os.environ["MODE"] = "AUTOMATION"
    log_pulse("STEP 3: Set MODE=AUTOMATION to prevent blocking inputs")
    
    # 4. Construct Command
    target_script = "volatilityhunter.py"
    if not os.path.exists(target_script):
        log_pulse(f"[CRITICAL] {target_script} not found in current folder!")
        return
    
    cmd = [python_exe, "-u", target_script, "--mode", "trading"]
    log_pulse(f"STEP 4: Launching: {' '.join(cmd)}")
    
    # 5. Run Process with timeout and error capture
    try:
        # Launch with pipes to capture errors
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=current_dir,
            env=os.environ.copy()  # Pass environment with MODE=AUTOMATION
        )
        
        # Wait for result with timeout
        try:
            stdout, stderr = process.communicate(timeout=900)  # 15 minute timeout
        except subprocess.TimeoutExpired:
            log_pulse("ERROR: Process timed out after 15 minutes - killing")
            process.kill()
            stdout, stderr = process.communicate()
        
        # Log full output line by line for complete debugging
        if stdout:
            for line in stdout.split('\n'):
                if line.strip():  # Only log non-empty lines
                    log_pulse(f"[CHILD] {line.strip()}")
        
        if stderr:
            for line in stderr.split('\n'):
                if line.strip():  # Only log non-empty lines
                    log_pulse(f"[CHILD ERROR] {line.strip()}")
        
        log_pulse(f"STEP 5: Finished with Exit Code: {process.returncode}")
        
        # Return the exit code
        return process.returncode
        
    except Exception as e:
        log_pulse(f"[CRITICAL FAILURE] {e}")
        return 1

if __name__ == "__main__":
    main()
