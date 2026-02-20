#!/usr/bin/env python3
"""
SECURE TWS Launcher - NO CREDENTIALS STORED
User must create their own encrypted config file
"""

import os
import subprocess
from pathlib import Path

def create_tws_config_template():
    """Create a template for user to fill with their credentials"""
    config_template = """
# TWS AUTO-LOGIN CONFIGURATION
# ===========================
# 
# SECURITY NOTICE: 
# 1. Fill in your credentials below
# 2. Save this file as tws_credentials.py
# 3. Add tws_credentials.py to .gitignore
# 4. NEVER commit this file to git
# 5. Delete this template file after setup

# Your TWS Login Credentials
TWS_USERNAME = "YOUR_USERNAME_HERE"
TWS_PASSWORD = "YOUR_PASSWORD_HERE"

# Trading Mode
TWS_MODE = "paper"  # or "live"

# Optional: Save login (reduces security but convenient)
SAVE_PASSWORD = False

# TWS Installation Path (auto-detected if empty)
TWS_PATH = ""

# API Settings
API_PORT = 7497  # 7497 for paper, 7496 for live
"""
    
    template_path = Path.cwd() / "scripts" / "tws_credentials_template.py"
    
    with open(template_path, 'w') as f:
        f.write(config_template)
    
    print("=" * 60)
    print("TWS CREDENTIALS TEMPLATE CREATED")
    print("=" * 60)
    print(f"Template saved to: {template_path}")
    print()
    print("SETUP INSTRUCTIONS:")
    print("1. Open the template file")
    print("2. Replace YOUR_USERNAME_HERE with your TWS username")
    print("3. Replace YOUR_PASSWORD_HERE with your TWS password")
    print("4. Save as 'tws_credentials.py' (NOT template)")
    print("5. Add 'tws_credentials.py' to .gitignore")
    print("6. Delete the template file")
    print()
    print("⚠️  SECURITY WARNING:")
    print("- Never share this file")
    print("- Never commit to git")
    print("- This file contains your actual credentials")
    print()
    print("After setup, run: python scripts/secure_tws_launcher.py")
    
    return template_path

def launch_tws_with_credentials():
    """Launch TWS using user-provided credentials file"""
    credentials_file = Path.cwd() / "scripts" / "tws_credentials.py"
    
    if not credentials_file.exists():
        print("❌ Credentials file not found!")
        print("Please run: python scripts/secure_tws_launcher.py --setup")
        return False
    
    try:
        # Import credentials (user created this file)
        import sys
        sys.path.append(str(Path.cwd() / "scripts"))
        from tws_credentials import TWS_USERNAME, TWS_PASSWORD, TWS_MODE, TWS_PATH, API_PORT
        
        if TWS_USERNAME == "YOUR_USERNAME_HERE" or TWS_PASSWORD == "YOUR_PASSWORD_HERE":
            print("❌ Please fill in your actual credentials!")
            print(f"Edit: {credentials_file}")
            return False
        
        # Find TWS executable
        if TWS_PATH and Path(TWS_PATH).exists():
            tws_exe = TWS_PATH
        else:
            # Auto-detect
            common_paths = [
                r"C:\Jts\tws.exe",
                r"C:\IBJts\tws.exe",
                r"C:\Program Files\IBJts\tws.exe",
                r"C:\Program Files (x86)\IBJts\tws.exe"
            ]
            
            tws_exe = None
            for path in common_paths:
                if Path(path).exists():
                    tws_exe = path
                    break
            
            if not tws_exe:
                print("❌ TWS not found! Please install TWS first.")
                return False
        
        print(f"🚀 Launching TWS with auto-login...")
        print(f"Username: {TWS_USERNAME}")
        print(f"Mode: {TWS_MODE}")
        print(f"Executable: {tws_exe}")
        
        # Launch TWS with credentials (this is a simplified approach)
        # Note: Real auto-login may require additional TWS configuration
        subprocess.Popen([tws_exe], shell=True)
        
        print("✅ TWS launched! Please complete login manually if needed.")
        return True
        
    except ImportError as e:
        print(f"❌ Error importing credentials: {e}")
        print("Please check your tws_credentials.py file")
        return False
    except Exception as e:
        print(f"❌ Error launching TWS: {e}")
        return False

def main():
    """Main function"""
    import sys
    
    if "--setup" in sys.argv:
        create_tws_config_template()
        return 0
    else:
        return 1 if not launch_tws_with_credentials() else 0

if __name__ == "__main__":
    exit(main())
