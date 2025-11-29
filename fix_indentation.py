
import os

file_path = r"d:\one cloud\OneDrive\Desktop\bolna.ai\bolna\sunona\agent_manager\task_manager.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines are 0-indexed in list, so line 278 is index 277.
# We want to dedent from line 278 (index 277) to the end of __init__.
# __init__ ends when we see "def " or class level indentation.
# Based on previous views, __init__ ends around line 365.
# Let's find the range dynamically.

start_index = 277 # Line 278
end_index = -1

for i in range(start_index, len(lines)):
    line = lines[i]
    # Check if we hit the next method definition
    if line.strip().startswith("def "):
        end_index = i
        break

if end_index == -1:
    print("Could not find end of __init__")
    exit(1)

print(f"Dedenting lines {start_index+1} to {end_index}")

for i in range(start_index, end_index):
    line = lines[i]
    if line.strip() == "":
        continue
    
    # Check if it has at least 12 spaces (since we want to remove 4)
    # But wait, some lines might be further indented. We just want to remove 4 spaces from the start.
    if line.startswith("            "): # 12 spaces
        lines[i] = line[4:]
    elif line.startswith("        "): # 8 spaces - this shouldn't happen if everything is indented, but just in case
        # If it's already 8 spaces, maybe we shouldn't touch it?
        # But the issue is that they ARE at 12 spaces.
        pass
    else:
        print(f"Warning: Line {i+1} has unexpected indentation: {repr(line)}")

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Done.")
