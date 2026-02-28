#!/usr/bin/env python3
"""
Fix imports in all testing files after moving to root
"""

import os
import re

def fix_imports_in_file(file_path):
    """Fix imports in a single file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix the import path
        old_pattern = r"sys\.path\.insert\(0, os\.path\.join\(os\.path\.dirname\(__file__\), 'src'\)\)"
        new_pattern = """vh_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, vh_root)
sys.path.insert(0, os.path.join(vh_root, 'src'))"""
        
        content = re.sub(old_pattern, new_pattern, content)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Fixed imports in {os.path.basename(file_path)}")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

# Fix all agent test files
test_files = [
    "testing/agents_tests/test_data_agent.py",
    "testing/agents_tests/test_strategy_agent.py", 
    "testing/agents_tests/test_execution_agent.py",
    "testing/agents_tests/test_sync_agent.py",
    "testing/agents_tests/test_notification_agent.py",
    "testing/agents_tests/test_scheduler_agent.py",
    "testing/agents_tests/test_testing_agent.py"
]

for file_path in test_files:
    fix_imports_in_file(file_path)

print("🎉 All import fixes completed!")
