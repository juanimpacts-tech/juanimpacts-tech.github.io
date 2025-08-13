import yaml, regex as re

def _load_rules(rules_dir: str):
    with open(f"{rules_dir}/protected.yaml", "r", encoding="utf-8") as f:
        protected = yaml.safe_load(f) or {}
    with open(f"{rules_dir}/patterns.yaml", "r", encoding="utf-8") as f:
        patterns_cfg = yaml.safe_load(f) or {}
    patterns = []
    for p in patterns_cfg.get("patterns", []):
        patterns.append((p["name"], re.compile(p["regex"], re.IGNORECASE)))
    # flatten protected terms (case-insensitive match)
    terms = []
    for k, vals in protected.items():
        for v in (vals or []):
            if isinstance(v, str) and v.strip():
                terms.append((k, v.strip()))
    return terms, patterns

def _dedupe_rects(rects):
    seen = set()
    out = []
    for r in rects:
        key = tuple(round(x, 2) for x in r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out

def build_manifest(page_num: int, page, page_text: str, rules_dir="rules"):
    """
    Return a list of detection dicts for this page:
    {page, bbox, text, label, source, confidence, action, reason}
    """
    terms, patterns = _load_rules(rules_dir)
    detections = []

    # 1) Protected terms (deterministic)
    lower_text = page_text.lower()
    for label, term in terms:
        t = term.strip()
        if not t: continue
        # naive contains
        if t.lower() in lower_text:
            # find visible quads via exact search_for
            rects = [r for r in page.search_for(t, quads=False)]
            rects = _dedupe_rects([ (r.x0, r.y0, r.x1, r.y1) for r in rects ])
            for r in rects:
                detections.append({
                    "page": page_num,
                    "bbox": list(r),
                    "text": t,
                    "label": label,
                    "source": "keyword",
                    "confidence": 1.0,
                    "action": "redact",
                    "reason": f"Protected {label}"
                })

    # 2) Regex patterns (PII-like)
    for pname, pregex in patterns:
        for m in pregex.finditer(page_text):
            matched = m.group(0)
            rects = [r for r in page.search_for(matched, quads=False)]
            rects = _dedupe_rects([ (r.x0, r.y0, r.x1, r.y1) for r in rects ])
            for r in rects:
                detections.append({
                    "page": page_num,
                    "bbox": list(r),
                    "text": matched,
                    "label": pname,
                    "source": "regex",
                    "confidence": 0.99,
                    "action": "redact",
                    "reason": f"Pattern {pname}"
                })

    return detections
