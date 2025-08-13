import json, os

DATA_DIR = "data"

def save_manifest(job_id: str, manifest: dict, decision: dict):
    payload = {"manifest": manifest, "decision": decision}
    with open(os.path.join(DATA_DIR, f"{job_id}_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def load_manifest(job_id: str):
    path = os.path.join(DATA_DIR, f"{job_id}_manifest.json")
    if not os.path.exists(path): return None
    import json
    return json.load(open(path, "r", encoding="utf-8"))
