import json
import os

files_to_recover = [
    "test_retrieval.py",
    "test_isolation.py",
    "test_ingestion.py"
]

transcript_path = r"C:\Users\USER\.gemini\antigravity-ide\brain\8d8fd52f-f436-4a29-ba93-2b206a070c9f\.system_generated\logs\transcript_full.jsonl"

recovered = {}

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if "tool_calls" in data:
                for tc in data["tool_calls"]:
                    name = tc.get("name") or tc.get("function", {}).get("name")
                    if name == "default_api:write_to_file" or name == "write_to_file":
                        args_raw = tc.get("arguments") or tc.get("function", {}).get("arguments")
                        if isinstance(args_raw, str):
                            args = json.loads(args_raw)
                        else:
                            args = args_raw
                            
                        if args:
                            target = args.get("TargetFile")
                            if target:
                                basename = os.path.basename(target)
                                if basename in files_to_recover:
                                    recovered[basename] = args.get("CodeContent")
        except Exception:
            pass

mapping = {
    "test_retrieval.py": r"c:\Users\USER\Desktop\saas projects\research_agent\tests\test_services\test_retrieval.py",
    "test_isolation.py": r"c:\Users\USER\Desktop\saas projects\research_agent\tests\test_isolation.py",
    "test_ingestion.py": r"c:\Users\USER\Desktop\saas projects\research_agent\tests\test_api\test_ingestion.py"
}

for basename, content in recovered.items():
    content = content.replace("db_session", "async_session")
    out_path = mapping[basename]
    with open(out_path, "w", encoding="utf-8") as out:
        out.write(content)
    print(f"Recovered {out_path}")
