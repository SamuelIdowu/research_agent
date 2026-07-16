import httpx
import json
import os
import sys

def main():
    api_key = os.getenv("RA_KEY", "test_api_key")
    client_id = os.getenv("CLIENT_ID", "00000000-0000-0000-0000-000000000000")
    
    url = "http://localhost:8000/generate?stream=true"
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "brief": "Short test",
        "client_id": client_id
    }

    print(f"Connecting to {url}...")
    try:
        with httpx.stream("POST", url, headers=headers, json=payload, timeout=60.0) as response:
            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code}")
                print(response.read().decode("utf-8"))
                sys.exit(1)
                
            for line in response.iter_lines():
                if not line:
                    continue
                
                if line.startswith("0:"):
                    content = json.loads(line[2:])
                    print(f'[TEXT] {json.dumps(content)}')
                elif line.startswith("8:"):
                    data = json.loads(line[2:])
                    print(f'[DATA] {json.dumps(data)}')
                elif line.startswith("d:"):
                    data = json.loads(line[2:])
                    print(f'[DATA] {json.dumps(data)}')
                    print("[DONE]")
                    break
                elif line.startswith("3:"):
                    error = json.loads(line[2:])
                    print(f'[ERROR] {error}')
                    break
                else:
                    print(f'[UNKNOWN] {line}')
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
