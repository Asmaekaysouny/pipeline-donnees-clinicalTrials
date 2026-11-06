import json
import os

import requests

URL = "https://clinicaltrials.gov/api/v2/studies"
params = {"query.cond": "breast cancer", "pageSize": 100}

r = requests.get(URL, params=params, timeout=30)
r.raise_for_status()

os.makedirs("tests/fixtures", exist_ok=True)
with open("tests/fixtures/sample_page.jsonl", "w", encoding="utf-8") as f:
    for study in r.json()["studies"]:
        f.write(json.dumps(study, ensure_ascii=False) + "\n")
