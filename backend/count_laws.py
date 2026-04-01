import json
import os

path = r"d:\develop1\law03\backend\data\laws_processed.jsonl"
if not os.path.exists(path):
    print(f"File not found: {path}")
    exit()

unique_files = set()
total_lines = 0
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        total_lines += 1
        try:
            data = json.loads(line)
            unique_files.add(data.get('file_name'))
        except:
            pass

print(f"Total lines in JSONL: {total_lines}")
print(f"Unique files in JSONL: {len(unique_files)}")
for f in sorted(list(unique_files)):
    print(f" - {f}")
