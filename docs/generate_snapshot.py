import os

# The file we will create
OUTPUT_FILE = "project_snapshot.txt"

# Folders to ignore (Noise & Data)
IGNORE_DIRS = {'.git', '__pycache__', 'venv', 'env', 'archive', 'backup', '.windsurf', 'data', 'logs', '.idea', '.vscode'}

# File extensions to include (Signal)
INCLUDE_EXT = {'.py', '.md', '.json', '.bat', '.sh', '.txt', '.windsurfrules'}

def generate_snapshot():
    print(f"📸 Generating snapshot to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        # 1. Write the Directory Tree
        outfile.write("=== PROJECT STRUCTURE ===\n")
        for root, dirs, files in os.walk("."):
            # Filter directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            level = root.replace(".", "").count(os.sep)
            indent = " " * 4 * (level)
            outfile.write(f"{indent}{os.path.basename(root)}/\n")
            subindent = " " * 4 * (level + 1)
            for f in files:
                if any(f.endswith(ext) for ext in INCLUDE_EXT) or f in ['requirements.txt', 'Dockerfile']:
                    outfile.write(f"{subindent}{f}\n")
        
        outfile.write("\n\n=== FILE CONTENTS ===\n")
        
        # 2. Write File Contents
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for file in files:
                if any(file.endswith(ext) for ext in INCLUDE_EXT) or file in ['requirements.txt', 'Dockerfile']:
                    path = os.path.join(root, file)
                    # Skip the snapshot file itself to avoid recursion
                    if file == OUTPUT_FILE:
                        continue
                        
                    outfile.write(f"\n{'='*80}\n")
                    outfile.write(f"--- START FILE: {path} ---\n")
                    outfile.write(f"{'='*80}\n")
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            outfile.write(f.read())
                    except Exception as e:
                        outfile.write(f"[Error reading file: {e}]")
                    outfile.write(f"\n--- END FILE: {path} ---\n")

    print(f"✅ Snapshot generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_snapshot()
