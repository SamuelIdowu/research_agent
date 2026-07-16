import re

with open(r'C:\Users\USER\.gemini\antigravity-ide\brain\8d8fd52f-f436-4a29-ba93-2b206a070c9f\.system_generated\logs\transcript_full.jsonl', encoding='utf-8') as f:
    content = f.read()
    targets = re.findall(r'"TargetFile"\\?\s*:\s*\\?"([^"\\]+)\\?"', content)
    print(set(targets))
