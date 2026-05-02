#!/usr/bin/env python3
"""
IBC LOG DIAGNOSTIC TOOL
========================
Extracts and displays the most recent IBC log entries for debugging.
"""

import os
import sys
import glob
from pathlib import Path
from datetime import datetime

def find_ibc_log_directory():
    """Find IBC log directory in common locations."""
    potential_paths = [
        Path(r"C:\IBC\Logs"),
        Path(os.path.expanduser(r"~\IBC\Logs")),
        Path(os.path.expanduser(r"~\AppData\Local\IBC\Logs")),
        Path(r"C:\Program Files\IBC\Logs"),
    ]
    
    for path in potential_paths:
        if path.exists() and path.is_dir():
            print(f"Found IBC log directory: {path}")
            return path
    
    # Search for IBC directories more broadly
    for drive in ['C:', 'D:']:
        try:
            drive_path = Path(drive)
            if drive_path.exists():
                for item in drive_path.rglob("IBC"):
                    log_dir = item / "Logs"
                    if log_dir.exists() and log_dir.is_dir():
                        print(f"Found IBC log directory via search: {log_dir}")
                        return log_dir
        except (PermissionError, OSError):
            continue
    
    return None

def get_most_recent_log_file(log_dir):
    """Get the most recently modified log file from IBC log directory."""
    if not log_dir:
        return None
    
    # Look for various log file extensions
    log_patterns = [
        "*.txt",
        "*.log", 
        "*.out",
        "IBC_*.txt",
        "ibc_*.log",
        "*gateway*.log"
    ]
    
    log_files = []
    for pattern in log_patterns:
        log_files.extend(log_dir.glob(pattern))
        log_files.extend(log_dir.glob(pattern.lower()))
    
    if not log_files:
        # Try subdirectories
        for subdir in log_dir.iterdir():
            if subdir.is_dir():
                for pattern in log_patterns:
                    log_files.extend(subdir.glob(pattern))
                    log_files.extend(subdir.glob(pattern.lower()))
    
    if not log_files:
        return None
    
    # Sort by modification time (most recent first)
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    most_recent = log_files[0]
    print(f"Most recent log file: {most_recent}")
    print(f"Modified: {datetime.fromtimestamp(most_recent.stat().st_mtime)}")
    
    return most_recent

def dump_log_tail(log_file, lines=50):
    """Print the last N lines of the log file."""
    if not log_file or not log_file.exists():
        print("No log file found!")
        return
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
        
        # Get last N lines
        tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        print(f"\n{'='*80}")
        print(f"IBC LOG TAIL - Last {len(tail_lines)} lines")
        print(f"{'='*80}")
        
        for i, line in enumerate(tail_lines, 1):
            print(f"{i:3d}: {line.rstrip()}")
        
        print(f"\n{'='*80}")
        print(f"Full log file: {log_file}")
        print(f"Total lines: {len(all_lines)}")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"Error reading log file: {e}")

def main():
    print("IBC LOG DIAGNOSTIC TOOL")
    print("="*50)
    
    # Find IBC log directory
    log_dir = find_ibc_log_directory()
    if not log_dir:
        print("ERROR: IBC log directory not found!")
        print("Checked locations:")
        print("  - C:\\IBC\\Logs")
        print("  - ~\\IBC\\Logs") 
        print("  - ~\\AppData\\Local\\IBC\\Logs")
        print("  - C:\\Program Files\\IBC\\Logs")
        return
    
    # Get most recent log file
    log_file = get_most_recent_log_file(log_dir)
    if not log_file:
        print("ERROR: No log files found in IBC directory!")
        return
    
    # Dump log tail
    dump_log_tail(log_file, lines=50)

if __name__ == "__main__":
    main()
