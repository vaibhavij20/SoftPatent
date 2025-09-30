import json
from pathlib import Path

def store_feedback(body, out_file):
    p = Path(out_file)
    with p.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(body) + '\n')
