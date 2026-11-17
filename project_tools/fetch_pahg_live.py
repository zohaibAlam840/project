"""Resumable capture of official PAHG per-family FASTA downloads.

Downloads are stored by official family ID, separate from GitHub and supplied
files. Bad HTTP responses are never accepted as FASTA. A manifest records the
exact URL, SHA256, retrieval date and any failed attempts.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = json.loads((ROOT / "inventory" / "pahg_live_catalogue.json").read_text(encoding="utf-8"))
DEST = ROOT / "online_sources" / "PAHG_live_2026-11-18"
MANIFEST = ROOT / "inventory" / "pahg_live_download_manifest.json"
BASE = "https://www.pahgncb.com/genomedb/public/download"


def download(fid: int, kind: str) -> dict:
    endpoint = "alignment" if kind == "alignment" else "seqs"
    url = f"{BASE}/{endpoint}/{fid}"
    output = DEST / f"{fid:04d}_{kind}.fasta"
    if output.exists():
        data = output.read_bytes()
        if data and not re.search(rb"(?m)^>[^\r\n]+", data):
            raise ValueError(f"Existing capture is not FASTA: {output}")
        status = "captured"
    else:
        status = "failed"
        data = b""
        for attempt in range(3):
            with tempfile.NamedTemporaryFile(dir=DEST, suffix=".part", delete=False) as stream:
                temporary = Path(stream.name)
            try:
                result = subprocess.run([
                    "curl.exe", "-fSL", "-sS", "--connect-timeout", "8", "--max-time", "30",
                    "-o", str(temporary), "-w", "%{http_code}", url,
                ], capture_output=True, text=True, timeout=38)
                if result.returncode == 0 and result.stdout.strip() == "200":
                    data = temporary.read_bytes()
                    if not data or re.search(rb"(?m)^>[^\r\n]+", data):
                        temporary.replace(output)
                        status = "captured" if data else "empty"
                        break
                error = f"curl={result.returncode} http={result.stdout.strip()} {result.stderr.strip()[:120]}"
            except subprocess.TimeoutExpired:
                error = "curl timeout"
            finally:
                if temporary.exists():
                    temporary.unlink()
            time.sleep(1 + attempt)
    return {"family_id": fid, "kind": kind, "url": url,
            "path": str(output.relative_to(ROOT)).replace("\\", "/") if output.exists() else "",
            "status": status, "bytes": len(data) if output.exists() else 0,
            "sha256": hashlib.sha256(data).hexdigest() if output.exists() else "",
            "retrieved_utc": datetime.now(timezone.utc).isoformat() if status in ("captured", "empty") else "",
            "error": error if status == "failed" else ""}


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    prior = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"rows": []}
    rows = {(int(row["family_id"]), row["kind"]): row for row in prior["rows"]}
    ids = [int(row["href"].rsplit("/", 1)[-1]) for row in CATALOGUE["rows"]]
    assert len(ids) == len(set(ids)) == 221
    for index, fid in enumerate(ids, 1):
        for kind in ("alignment", "sequence"):
            key = (fid, kind)
            if key in rows and rows[key]["status"] in ("captured", "empty") and (ROOT / rows[key]["path"]).exists():
                continue
            rows[key] = download(fid, kind)
            MANIFEST.write_text(json.dumps({"source": BASE, "rows": list(rows.values())}, indent=2), encoding="utf-8")
        if index % 10 == 0:
            print(f"Processed {index}/221 families; captured {sum(r['status']=='captured' for r in rows.values())} files; failures {sum(r['status']=='failed' for r in rows.values())}", flush=True)
        time.sleep(0.2)
    print(f"Finished {len(rows)} endpoints; captured {sum(r['status']=='captured' for r in rows.values())}, empty {sum(r['status']=='empty' for r in rows.values())}, failed {sum(r['status']=='failed' for r in rows.values())}")


if __name__ == "__main__":
    main()
