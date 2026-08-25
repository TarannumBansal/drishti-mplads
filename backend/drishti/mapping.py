"""Auto-detect source columns and map them to the canonical Drishti schema.
Nothing is fabricated: unmapped canonical fields simply stay absent."""
import re
from .schema import CANONICAL, BY_NAME

def _norm(s): return re.sub(r"[^a-z0-9 ]", " ", str(s).lower()).strip()

def detect_mapping(source_columns):
    """Return {canonical_field: source_column or None} using alias matching."""
    norm = {_norm(c): c for c in source_columns}
    mapping = {}
    used = set()
    for f in CANONICAL:
        hit = None
        # exact canonical name / alias match first
        for cand in (f.name.replace("_", " "),) + f.aliases:
            if _norm(cand) in norm and norm[_norm(cand)] not in used:
                hit = norm[_norm(cand)]; break
        # fuzzy contains match as fallback
        if not hit:
            for nc, orig in norm.items():
                if orig in used: continue
                padded = " " + nc + " "
                if any(_norm(a) and (" " + _norm(a) + " ") in padded for a in f.aliases):
                    hit = orig; break
        if hit:
            mapping[f.name] = hit; used.add(hit)
        else:
            mapping[f.name] = None
    return mapping

def apply_mapping(df, mapping):
    """Rename source columns to canonical names; drop unmapped source columns."""
    rename = {src: canon for canon, src in mapping.items() if src is not None}
    out = df.rename(columns=rename)
    keep = [c for c in BY_NAME if c in out.columns]
    return out[keep].copy()

def mapping_report(mapping, source_columns):
    mapped = {k: v for k, v in mapping.items() if v}
    missing_required = [k for k in ("work_id","sanctioned_amount") if not mapping.get(k)]
    unmapped_source = [c for c in source_columns if c not in mapping.values()]
    return {"mapped": mapped,
            "missing_canonical": [k for k, v in mapping.items() if not v],
            "missing_required": missing_required,
            "unmapped_source_columns": unmapped_source}
