import os

input_dir = r"d:\develop1\law03\knowledge_base\laws"
files = os.listdir(input_dir)

for f in files:
    if f.endswith(".docx"):
        path = os.path.join(input_dir, f)
        with open(path, 'rb') as fd:
            header = fd.read(4)
        print(f"{f}: {header}")
