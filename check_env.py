#!/usr/bin/env python3
"""
Environment checker for Unknown Chat Bot.
This script checks if all required dependencies are installed and compatible.
"""

import sys
import importlib.util
import os
import platform

def check_module(module_name, min_version=None):
    """Check if a module is installed and meets minimum version."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"❌ {module_name} is not installed")
            return False
        
        if min_version:
            mod = importlib.import_module(module_name)
            if hasattr(mod, '__version__'):
                version = mod.__version__
                print(f"✅ {module_name} {version} installed")
                if version < min_version:
                    print(f"⚠️  Warning: {module_name} {version} is older than recommended ({min_version})")
                return True
            else:
                print(f"✅ {module_name} installed (version unknown)")
                return True
        else:
            print(f"✅ {module_name} installed")
            return True
    except Exception as e:
        print(f"❌ Error checking {module_name}: {e}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version.split()[0]
    print(f"Python version: {version}")
    
    major, minor, *_ = version.split('.')
    major, minor = int(major), int(minor)
    
    if major == 3 and 7 <= minor <= 12:
        print("✅ Python version is fully compatible")
    else:
        print("⚠️  This bot is recommended to run on Python 3.7-3.12")
        print("   Python 3.11.x is the recommended version")
    
    return True

def main():
    """Run all environment checks."""
    print("="*50)
    print("Unknown Chat Bot - Environment Checker")
    print("="*50)
    print()
    
    # Check Python version
    print("Checking Python version...")
    python_check = check_python_version()
    print()
    
    # Check required modules
    print("Checking required modules...")
    modules_check = True
    
    required_modules = [
        ('telegram', '13.15'),
        ('pytz', None),
        ('tzlocal', None),
        ('tabulate', None),
        ('apscheduler', None),
        ('urllib3', '1.26'),
    ]
    
    for module, min_version in required_modules:
        if not check_module(module, min_version):
            modules_check = False
    
    print()
    
    # Check for required directories
    print("Checking required directories...")
    if not os.path.exists('chat_logs'):
        print("❌ chat_logs directory not found, please create it with 'mkdir chat_logs'")
        dirs_check = False
    else:
        print("✅ chat_logs directory found")
        dirs_check = True
    
    if not os.path.exists('config.py'):
        print("⚠️  config.py not found, bot token needs to be configured")
    else:
        print("✅ config.py found")
    
    print()
    
    # Summary
    print("="*50)
    print("Environment Check Summary")
    print("="*50)
    
    if all([python_check, modules_check, dirs_check]):
        print("✅ All checks passed! Your environment is ready to run the bot.")
    else:
        print("⚠️  Some checks failed. Please fix the issues before running the bot.")
    
    print()
    print("For more information, see SETUP.md")
    print()

if __name__ == "__main__":
    main() 