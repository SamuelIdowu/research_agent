import json
from src.main import app

with open('openapi_dump.json', 'w') as f:
    json.dump(app.openapi(), f, indent=2)
