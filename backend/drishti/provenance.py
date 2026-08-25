import hashlib, datetime, uuid
def make_provenance(base, df, user="local"):
    h = hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()[:16]
    return {**base, "import_id": str(uuid.uuid4())[:8], "import_user": user,
            "imported_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "checksum": h, "schema_version": "1.0"}
