import json, subprocess, os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
hits = json.load(open("gh/hits.json"))
os.makedirs("gh/files", exist_ok=True)
jobs = [(m, *x) for m, lst in hits.items() for x in lst]
def get(j):
    m, repo, path, sha = j
    fn = f"gh/files/{sha}.txt"
    if os.path.exists(fn) and os.path.getsize(fn) > 0: return 1
    r = subprocess.run(["curl", "-sS", "-m", "30", "--max-filesize", "2000000", "-f", "-o", fn, f"https://raw.githubusercontent.com/{repo}/HEAD/{quote(path)}"], capture_output=True, text=True)
    return int(r.returncode == 0)
with ThreadPoolExecutor(6) as ex: res = list(ex.map(get, jobs))
print(len(jobs), sum(res))
