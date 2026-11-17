"""Create traceable working FASTAs; only repair missing header line breaks.

This changes no residue, gap, or label character. Empty and truncated source
files remain visibly incomplete and are never filled with guessed sequence.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from audit_public_fastas import audit

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "inventory"
SOURCE = ROOT / "online_sources" / "PAHG_GitHub_83e042106746"
DEST = ROOT / "working_copies" / "public_fastas"
manifest = json.loads((INV / "public_fasta_manifest.json").read_text(encoding="utf-8"))


def normalize(data: bytes) -> tuple[bytes, int]:
    # In these files, a '>' inside a sequence line starts the next FASTA
    # header. Require a following newline and visible header text.
    out = bytearray()
    repairs = 0
    for index, byte in enumerate(data):
        if byte == ord(">") and index and data[index - 1] not in (10, 13):
            end = data.find(b"\n", index)
            header = data[index + 1:end if end >= 0 else len(data)]
            if len(header.strip()) < 5 or any(c < 32 and c != 13 for c in header):
                raise ValueError(f"Ambiguous embedded FASTA header at byte {index}")
            out.extend(b"\n")
            repairs += 1
        out.append(byte)
    return bytes(out), repairs


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    rows = []
    for entry in manifest["files"]:
        name = Path(entry["path"]).name
        original = (SOURCE / name).read_bytes()
        cleaned, repairs = normalize(original)
        target = DEST / name
        if target.exists() and target.read_bytes() != cleaned:
            raise ValueError(f"Existing working copy differs: {target}")
        target.write_bytes(cleaned)
        checked = audit(target)
        if checked["embedded_header_markers"] or checked["invalid_characters"].replace("_", ""):
            raise ValueError(f"Working copy still has broken FASTA syntax: {name}")
        rows.append({
            "filename": name, "source_path": entry["path"],
            "source_sha256": entry["sha256"],
            "working_path": str(target.relative_to(ROOT)).replace("\\", "/"),
            "working_sha256": hashlib.sha256(cleaned).hexdigest(),
            "inserted_header_line_breaks": repairs,
            "working_records": checked["records"],
            "remaining_issue": ("EMPTY SOURCE" if checked["records"] == 0
                                else "SOURCE ALIGNMENT TRUNCATED" if checked["kind"] == "alignment"
                                and checked["equal_lengths"] != "YES"
                                else "SOURCE HAS UNKNOWN RESIDUE '_'" if checked["invalid_characters"]
                                else ""),
        })
    (INV / "public_fasta_normalization.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with (INV / "public_fasta_normalization.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Created {len(rows)} working FASTAs; inserted {sum(r['inserted_header_line_breaks'] for r in rows)} missing header line breaks in {sum(bool(r['inserted_header_line_breaks']) for r in rows)} files")


if __name__ == "__main__":
    main()
