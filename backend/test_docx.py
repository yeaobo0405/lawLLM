from docx import Document
import os

files = [
    r"d:\develop1\law03\knowledge_base\laws\内蒙古自治区中医药条例_2022-05-26_2022-07-01_地方性法规_内蒙古自治区人民代表大会常务委员会_有效.docx",
    r"d:\develop1\law03\knowledge_base\laws\内蒙古自治区促进民族团结进步条例_2021-01-30_2021-05-01_地方性法规_内蒙古自治区人民代表大会常务委员会_有效.docx",
    r"d:\develop1\law03\knowledge_base\laws\内蒙古自治区反家庭暴力条例_2020-04-01_2020-05-01_地方性法规_内蒙古自治区人民代表大会常务委员会_有效.docx"
]

for f in files:
    print(f"Testing {os.path.basename(f)}...")
    try:
        doc = Document(f)
        print(f"  Success! Paragraphs: {len(doc.paragraphs)}")
    except Exception as e:
        print(f"  Failed: {e}")
