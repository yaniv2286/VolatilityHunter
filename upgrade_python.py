#!/usr/bin/env python3
"""
Python Version Upgrade Helper
Updates VolatilityHunter to latest Python version (3.11+)
"""

import subprocess
import sys
import os

def check_python_version():
    """Check current Python version"""
    version = sys.version_info
    print(f"Current Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ Python 3.11+ is required for VolatilityHunter")
        print("Please install Python 3.11+ from https://python.org")
        return False
    
    print("✅ Python version is compatible")
    return True

def update_dependencies():
    """Update all dependencies to latest versions"""
    print("\n📦 Updating dependencies...")
    
    try:
        # Update pip first
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        
        # Install requirements
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        
        print("✅ Dependencies updated successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to update dependencies: {e}")
        return False

def test_imports():
    """Test that all critical imports work"""
    print("\n🧪 Testing imports...")
    
    test_modules = [
        "pandas",
        "numpy", 
        "flask",
        "requests",
        "dotenv",
        "yfinance",
        "aiohttp"
    ]
    
    failed_imports = []
    
    for module in test_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed imports: {', '.join(failed_imports)}")
        return False
    
    print("✅ All imports successful")
    return True

def main():
    print("🚀 VolatilityHunter Python Upgrade Helper")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Update dependencies
    if not update_dependencies():
        sys.exit(1)
    
    # Test imports
    if not test_imports():
        sys.exit(1)
    
    print("\n🎉 Python upgrade completed successfully!")
    print("VolatilityHunter is now running with the latest Python version and dependencies.")

if __name__ == "__main__":
    main()
