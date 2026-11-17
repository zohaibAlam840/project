"""Capture every public FASTA at the pinned PAHG Git commit.

The files are evidence, not automatically accepted analysis inputs. Existing
files are checked against their Git blob hash and never silently replaced.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "83e0421067465e6855371fb65f99384855d23d80"
TREE = json.loads((ROOT / "project_tools" / "repo_tree.json").read_text(encoding="utf-8"))
DEST = ROOT / "online_sources" / f"PAHG_GitHub_{COMMIT[:12]}"
FILES = [item for item in TREE["tree"] if item["type"] == "blob"
         and item["path"].startswith("public/") and item["path"].lower().endswith(".fasta")]


def capture(item: dict) -> dict:
    relative = item["path"].removeprefix("public/")
    path = DEST / relative
    url = ("https://raw.githubusercontent.com/PAHG-Database/PAHG/" + COMMIT + "/"
           + urllib.parse.quote(item["path"]))
    if path.exists():
        data = path.read_bytes()
    else:
        data = None
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "PAHG-MPhil-data-audit"})
                with urllib.request.urlopen(request, timeout=40) as response:
                    data = response.read()
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        assert data is not None
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if blob != item["sha"]:
        raise ValueError(f"Git blob mismatch for {relative}")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "source_url": url,
            "git_blob": blob, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def main() -> None:
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(capture, item): item["path"] for item in FILES}
        rows = []
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: row["path"])
    output = ROOT / "inventory" / "public_fasta_manifest.json"
    output.write_text(json.dumps({"commit": COMMIT, "files": rows}, indent=2), encoding="utf-8")
    print(f"Verified {len(rows)} public FASTA files ({sum(r['bytes'] for r in rows):,} bytes)")


if __name__ == "__main__":
    main()
