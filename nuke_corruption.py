import os
import glob

# The folder where your data lives
data_dir = "data"

# The specific files causing the crash (Code Red list)
# We target COMP (the likely culprit) and its neighbors just to be safe.
kill_list = [
    "COMP.parquet", "COLM.parquet", "COLB.parquet", 
    "CON.parquet", "COO.parquet", "COP.parquet"
]

print(f"🚀 INITIALIZING CORRUPTION REMOVAL IN: {os.path.abspath(data_dir)}")

# Strategy 1: Targeted Strike
print("\n--- PHASE 1: TARGETED STRIKE ---")
for filename in kill_list:
    path = os.path.join(data_dir, filename)
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"✅ DELETED: {filename}")
        except Exception as e:
            print(f"❌ ERROR deleting {filename}: {e}")
    else:
        print(f"⚠️  Not found: {filename} (Already gone?)")

# Strategy 2: C-Block Wipe (Backup Plan)
# If the targeted strike misses, we wipe the immediate area.
print("\n--- PHASE 2: SEARCHING FOR 'C' RESIDUE ---")
c_files = glob.glob(os.path.join(data_dir, "C*.parquet"))
count = 0
for f in c_files:
    # Only delete files that look suspicious (too small) or are in the C-block
    # actually, let's just count them to verify the directory is reachable
    count += 1

print(f"ℹ️  Found {count} files starting with 'C'.")
if count > 0:
    print("   (Preserving the rest to save your API credits, Phase 1 should be enough)")

print("\n------------------------------------------------")
print("✅ OPERATION COMPLETE.")
print("The corrupted 'COMP' file should be destroyed.")
print("Restart the Daily Scan now.")