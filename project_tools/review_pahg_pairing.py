"""Record which sequences need manual review in format-passing PAHG families."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

from Bio import SeqIO

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "inventory"
audit = json.loads((INV / "pahg_live_audit.json").read_text(encoding="utf-8"))


def records(path: str) -> list[tuple[str, str]]:
    return [(rec.description, re.sub(r"\s", "", str(rec.seq)).upper().replace("-", ""))
            for rec in SeqIO.parse(ROOT / path, "fasta")]


def unmatched(left: list[tuple[str, str]], right: list[tuple[str, str]]) -> list[str]:
    available = Counter(seq for _, seq in right)
    missing = []
    for name, seq in left:
        if available[seq]:
            available[seq] -= 1
        else:
            missing.append(name)
    return missing


def main() -> None:
    rows = []
    for family in audit:
        if family["inventory_status"] != "FORMAT OR PAIRING REVIEW":
            continue
        raw = records(family["raw_working_path"])
        align = records(family["alignment_working_path"])
        raw_unmatched = unmatched(raw, align)
        aligned_unmatched = unmatched(align, raw)
        rows.append({
            "pahg_id": family["pahg_id"], "family_name": family["family_name"],
            "published_count": family["published_sequence_count"],
            "raw_records": len(raw), "aligned_records": len(align),
            "exact_sequence_matches": family["exact_ungapped_sequence_matches"],
            "raw_unmatched_count": len(raw_unmatched),
            "aligned_unmatched_count": len(aligned_unmatched),
            "raw_unmatched_headers": raw_unmatched,
            "aligned_unmatched_headers": aligned_unmatched,
            "raw_format_issue": family["raw_issues"],
            "alignment_format_issue": family["alignment_issues"],
        })
    (INV / "pairing_review_details.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    flattened = [{**row, "raw_unmatched_headers": " | ".join(row["raw_unmatched_headers"]),
                  "aligned_unmatched_headers": " | ".join(row["aligned_unmatched_headers"])} for row in rows]
    with (INV / "pairing_review_details.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flattened[0]))
        writer.writeheader()
        writer.writerows(flattened)
    print(f"Recorded sequence-level discrepancies for {len(rows)} families")


if __name__ == "__main__":
    main()
