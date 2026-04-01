import re
import cn2an

article_regex = re.compile(r'^(?:第([一二三四五六七八九十百零0-9]+)条|([一二三四五六七八九十百零0-9]+)[、.．])')

test_cases = [
    "第一条 土地所有权",
    "一、 土地所有权",
    "1. 土地所有权",
    "10、 土地所有权",
    "第十二条 抵押权"
]

for tc in test_cases:
    match = article_regex.match(tc)
    if match:
        raw_num = match.group(1) if match.group(1) else match.group(2)
        try:
            num = str(cn2an.cn2an(raw_num, "normal")) if not raw_num.isdigit() else raw_num
            print(f"Match: {tc} -> Num: {num}")
        except:
            print(f"Match: {tc} -> Raw: {raw_num} (Conversion failed)")
    else:
        print(f"No match: {tc}")
