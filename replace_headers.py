import os, glob, re

files = glob.glob('tests/e2e/*.py')
for f in files:
    with open(f, 'r') as file:
        content = file.read()
    
    # Replace headers dicts
    content = re.sub(r'"Authorization": f"Bearer \{([^}]+)\}"', r'"X-Api-Key": \1', content)
    content = re.sub(r'"Authorization": "Bearer ([^"]+)"', r'"X-Api-Key": "\1"', content)
    
    with open(f, 'w') as file:
        file.write(content)
print("Headers updated successfully!")
