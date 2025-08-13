import json, subprocess, tempfile, os, pathlib

def evaluate_manifest(manifest: dict, profile: str = "strict"):
    """
    Calls OPA to evaluate Rego policy. Requires 'opa' binary in PATH.
    """
    policy_dir = pathlib.Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as td:
        inp = os.path.join(td, "in.json")
        with open(inp, "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        # allow?
        r = subprocess.run(
            ["opa", "eval", "-f", "json", "-d", str(policy_dir / "redaction.rego"),
             "data.privypress.allow", "--input", inp],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            return {"profile": profile, "allow": False, "reasons": ["OPA eval error"], "stderr": r.stderr}
        allow = json.loads(r.stdout)["result"][0]["expressions"][0]["value"]
        # reasons
        r2 = subprocess.run(
            ["opa", "eval", "-f", "json", "-d", str(policy_dir / "redaction.rego"),
             "data.privypress.deny_reason", "--input", inp],
            capture_output=True, text=True
        )
        reasons = []
        if r2.returncode == 0:
            out = json.loads(r2.stdout)["result"][0]["expressions"][0]["value"]
            reasons = out if isinstance(out, list) else []
        return {"profile": profile, "allow": bool(allow), "reasons": reasons}
