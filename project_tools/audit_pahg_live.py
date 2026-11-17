"""Audit official PAHG downloads for every family without altering sources."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from Bio import SeqIO
from audit_public_fastas import audit
from normalize_public_fastas import normalize

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "inventory"
CATALOGUE = json.loads((INV / "pahg_live_catalogue.json").read_text(encoding="utf-8"))
DOWNLOADS = json.loads((INV / "pahg_live_download_manifest.json").read_text(encoding="utf-8"))
BY_KEY = {(int(row["family_id"]), row["kind"]): row for row in DOWNLOADS["rows"]}
DEST = ROOT / "working_copies" / "pahg_live_fastas"


def canonical_sequence(seq: str) -> str:
    return re.sub(r"\s", "", seq).upper().replace("-", "")


def inspect_file(fid: int, kind: str) -> dict:
    captured = BY_KEY.get((fid, kind), {})
    if captured.get("status") not in ("captured", "empty"):
        return {"status": "NOT CAPTURED", "records": 0, "path": ""}
    original = (ROOT / captured["path"]).read_bytes()
    if hashlib.sha256(original).hexdigest() != captured["sha256"]:
        raise ValueError(f"Capture hash changed: {fid} {kind}")
    cleaned, repairs = normalize(original)
    first_header = re.search(rb"(?m)^>", cleaned)
    preamble = cleaned[:first_header.start()] if first_header else b""
    if preamble:
        cleaned = cleaned[first_header.start():]
    working = DEST / f"{fid:04d}_{kind}.fasta"
    if working.exists() and working.read_bytes() != cleaned:
        raise ValueError(f"Working copy changed: {working}")
    working.write_bytes(cleaned)
    source_audit = audit(ROOT / captured["path"])
    working_audit = audit(working)
    if working_audit["embedded_header_markers"]:
        raise ValueError(f"Header repair failed: {fid} {kind}")
    return {"status": "CAPTURED" if original else "EMPTY", "records": working_audit["records"],
            "path": captured["path"], "working_path": str(working.relative_to(ROOT)).replace("\\", "/"),
            "sha256": captured["sha256"], "working_sha256": hashlib.sha256(cleaned).hexdigest(),
            "bytes": len(original), "equal_lengths": working_audit["equal_lengths"],
            "min_length": working_audit["min_length"], "max_length": working_audit["max_length"],
            "last_length": working_audit["last_length"], "embedded_headers_repaired": repairs,
            "preamble_bytes_removed": len(preamble),
            "source_issues": source_audit["issues"], "remaining_issues": working_audit["issues"],
            "invalid_characters": working_audit["invalid_characters"],
            "duplicate_headers": working_audit["duplicate_headers"]}


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    rows = []
    for page in CATALOGUE["rows"]:
        fid = int(page["href"].rsplit("/", 1)[-1])
        published = int(page["cells"][4]) if page["cells"][4].isdigit() else None
        align = inspect_file(fid, "alignment")
        raw = inspect_file(fid, "sequence")
        exact_matches = ""
        if align["records"] and raw["records"]:
            aligned_seqs = Counter(canonical_sequence(str(r.seq)) for r in SeqIO.parse(ROOT / align["working_path"], "fasta"))
            raw_seqs = Counter(canonical_sequence(str(r.seq)) for r in SeqIO.parse(ROOT / raw["working_path"], "fasta"))
            exact_matches = sum(min(count, aligned_seqs.get(seq, 0)) for seq, count in raw_seqs.items())
        if align["records"] == 0:
            status = "ALIGNMENT UNAVAILABLE"
        elif (align["equal_lengths"] != "YES"
              or (align.get("bytes") == 65535 and published is not None
                  and align["records"] < published and raw["records"] == published)):
            status = "ALIGNMENT INCOMPLETE"
        elif align["invalid_characters"] or align["duplicate_headers"]:
            status = "ALIGNMENT FORMAT ISSUE"
        else:
            status = "ALIGNMENT FORMAT PASSES"
        concordant = (status == "ALIGNMENT FORMAT PASSES"
                      and align["records"] == raw["records"] == published
                      and exact_matches == align["records"]
                      and not raw.get("remaining_issues"))
        inventory_status = ("SOURCE ALIGNMENT INCOMPLETE" if status == "ALIGNMENT INCOMPLETE"
                            else "SEQUENCE CHECKS PASS; PAHG TREE DOWNLOAD UNAVAILABLE" if concordant
                            else "FORMAT OR PAIRING REVIEW" if status == "ALIGNMENT FORMAT PASSES"
                            else "ALIGNMENT UNAVAILABLE")
        rows.append({
            "pahg_id": fid, "family_name": page["cells"][0],
            "published_sequence_count": published,
            "alignment_status": align["status"], "alignment_records": align["records"],
            "alignment_equal_lengths": align.get("equal_lengths", ""),
            "alignment_min_length": align.get("min_length", ""),
            "alignment_max_length": align.get("max_length", ""),
            "alignment_bytes": align.get("bytes", ""),
            "alignment_sha256": align.get("sha256", ""),
            "alignment_working_path": align.get("working_path", ""),
            "alignment_header_repairs": align.get("embedded_headers_repaired", ""),
            "alignment_preamble_bytes_removed": align.get("preamble_bytes_removed", ""),
            "alignment_issues": align.get("remaining_issues", ""),
            "raw_status": raw["status"], "raw_records": raw["records"],
            "raw_bytes": raw.get("bytes", ""), "raw_sha256": raw.get("sha256", ""),
            "raw_working_path": raw.get("working_path", ""),
            "raw_header_repairs": raw.get("embedded_headers_repaired", ""),
            "raw_preamble_bytes_removed": raw.get("preamble_bytes_removed", ""),
            "raw_issues": raw.get("remaining_issues", ""),
            "exact_ungapped_sequence_matches": exact_matches,
            "alignment_vs_published_count": (align["records"] - published if published is not None else ""),
            "raw_vs_published_count": (raw["records"] - published if published is not None else ""),
            "data_status": status,
            "sequence_concordant": "YES" if concordant else "NO",
            "inventory_status": inventory_status,
            "family_page": page["href"],
        })
    (INV / "pahg_live_audit.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with (INV / "pahg_live_audit.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("Families:", len(rows), "statuses:", dict(Counter(r["data_status"] for r in rows)))
    print("Inventory tiers:", dict(Counter(r["inventory_status"] for r in rows)))
    print("Downloaded:", sum(r["alignment_status"] == "CAPTURED" for r in rows), "alignments,",
          sum(r["raw_status"] == "CAPTURED" for r in rows), "raw files")
    print("Header repairs:", sum((r["alignment_header_repairs"] or 0) + (r["raw_header_repairs"] or 0) for r in rows))


if __name__ == "__main__":
    main()
