"""Audit the captured PAHG repository FASTAs without changing source data."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from Bio import SeqIO

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "inventory"
MANIFEST = json.loads((INV / "public_fasta_manifest.json").read_text(encoding="utf-8"))
PUBLIC = ROOT / "online_sources" / "PAHG_GitHub_83e042106746"
WORKING = ROOT / "working_copies" / "public_fastas"


def audit(path: Path) -> dict:
    data = path.read_bytes()
    text = data.decode("utf-8-sig", errors="replace")
    embedded_headers = sum(1 for i, char in enumerate(text) if char == ">" and i and text[i - 1] not in "\r\n")
    records: list[tuple[str, str]] = []
    header = None
    chunks: list[str] = []
    issues = []
    before_first_header = []
    for line_no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(chunks)))
            header, chunks = line[1:].strip(), []
            if not header:
                issues.append(f"empty header at line {line_no}")
        elif line:
            if header is None:
                before_first_header.append(line)
            else:
                chunks.append(line)
    if header is not None:
        records.append((header, "".join(chunks)))
    if before_first_header:
        issues.append("content before first FASTA header")
    if not data:
        issues.append("empty file")
    if data and not records:
        issues.append("no FASTA records")
    if embedded_headers:
        issues.append(f"{embedded_headers} header markers embedded in sequence lines")
    if "\ufffd" in text:
        issues.append("invalid UTF-8 bytes")
    empty = sum(not seq for _, seq in records)
    if empty:
        issues.append(f"{empty} empty sequences")
    headers = [head for head, _ in records]
    duplicates = sorted(head for head, n in Counter(headers).items() if n > 1)
    if duplicates:
        issues.append(f"{len(duplicates)} duplicate full headers")
    invalid = sorted(set("".join(seq for _, seq in records).upper()) - set("ABCDEFGHIJKLMNOPQRSTUVWXYZ-.*?"))
    if invalid:
        issues.append("unexpected sequence characters: " + repr("".join(invalid)))
    lengths = [len(seq) for _, seq in records]
    alignment = "alignment" in path.name.lower()
    equal = bool(lengths) and len(set(lengths)) == 1
    if alignment and not equal and lengths:
        issues.append("unequal alignment record lengths")
    # The PAHG live alignment download for ID 81 is exactly 65,535 bytes.
    # GitHub files have LF line endings; re-adding CR characters reveals
    # which files appear to have hit that exact upstream storage limit.
    crlf_size = len(data) + data.count(b"\n") if b"\r\n" not in data else len(data)
    at_text_limit = crlf_size == 65535
    if at_text_limit:
        issues.append("65,535-byte CRLF source limit reached; likely truncated")
    last_short = (alignment and len(lengths) > 1
                  and lengths[-1] < max(lengths[:-1])
                  and len(set(lengths[:-1])) == 1)
    if last_short:
        issues.append("last aligned sequence shorter than all preceding sequences")
    return {
        "filename": path.name, "bytes": len(data), "crlf_equivalent_bytes": crlf_size,
        "embedded_header_markers": embedded_headers,
        "kind": "alignment" if alignment else "sequence", "records": len(records),
        "unique_headers": len(set(headers)), "duplicate_headers": len(duplicates),
        "min_length": min(lengths, default=0), "max_length": max(lengths, default=0),
        "last_length": lengths[-1] if lengths else 0,
        "equal_lengths": "YES" if equal else "NO" if lengths else "EMPTY",
        "last_record_short": "YES" if last_short else "NO",
        "possible_65535_truncation": "YES" if at_text_limit else "NO",
        "invalid_characters": "".join(invalid), "issues": "; ".join(issues),
        "headers": headers,
    }


def main() -> None:
    source_rows = []
    for entry in MANIFEST["files"]:
        path = ROOT / entry["path"]
        row = audit(path)
        row.update({"source_url": entry["source_url"], "sha256": entry["sha256"]})
        source_rows.append(row)
    public = [{k: v for k, v in row.items() if k != "headers"} for row in source_rows]
    (INV / "public_fasta_audit.json").write_text(json.dumps(public, indent=2), encoding="utf-8")
    with (INV / "public_fasta_audit.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(public[0]))
        writer.writeheader()
        writer.writerows(public)
    by_filename = {row["filename"]: row for row in source_rows}
    with (INV / "online_candidates.csv").open(newline="", encoding="utf-8-sig") as stream:
        candidates = list(csv.DictReader(stream))
    family_rows = []
    for candidate in candidates:
        align = by_filename[candidate["alignment_fasta"]]
        raw = by_filename.get(candidate["raw_fasta"])
        raw_headers = set(raw["headers"]) if raw else set()
        aligned_headers = set(align["headers"])
        alignment_sequences = ({str(record.seq).upper().replace("-", "")
                                for record in SeqIO.parse(WORKING / align["filename"], "fasta")}
                               if (WORKING / align["filename"]).exists() else set())
        raw_sequences = ([str(record.seq).upper().replace("-", "")
                          for record in SeqIO.parse(WORKING / raw["filename"], "fasta")]
                         if raw and (WORKING / raw["filename"]).exists() else [])
        family_rows.append({
            "symbol": candidate["symbol"], "alignment_file": align["filename"],
            "alignment_records": align["records"], "alignment_sites_max": align["max_length"],
            "alignment_sites_min": align["min_length"], "equal_alignment_lengths": align["equal_lengths"],
            "last_record_short": align["last_record_short"],
            "possible_source_truncation": align["possible_65535_truncation"],
            "raw_file": raw["filename"] if raw else "",
            "raw_records": raw["records"] if raw else "",
            "exact_header_overlap": len(raw_headers & aligned_headers) if raw else "",
            "raw_headers_missing_from_alignment": len(raw_headers - aligned_headers) if raw else "",
            "alignment_headers_missing_from_raw": len(aligned_headers - raw_headers) if raw else "",
            "exact_ungapped_sequence_matches": sum(seq in alignment_sequences for seq in raw_sequences) if raw else "",
            "alignment_sha256": align["sha256"],
            "raw_sha256": raw["sha256"] if raw else "",
            "readiness": ("SOURCE INCOMPLETE" if align["equal_lengths"] != "YES"
                          else "ALIGNMENT FORMAT PASSES; TREE MISSING"),
            "review_note": align["issues"],
        })
    (INV / "online_family_audit.json").write_text(json.dumps(family_rows, indent=2), encoding="utf-8")
    with (INV / "online_family_audit.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(family_rows[0]))
        writer.writeheader()
        writer.writerows(family_rows)
    print("Public files:", len(public), "alignments:", sum(r["kind"] == "alignment" for r in public))
    print("Empty:", sum(r["records"] == 0 for r in public),
          "unaligned:", sum(r["kind"] == "alignment" and r["equal_lengths"] == "NO" for r in public),
          "65,535-byte candidates:", sum(r["possible_65535_truncation"] == "YES" for r in public))
    print("Candidate families:", Counter(r["readiness"] for r in family_rows))


if __name__ == "__main__":
    main()
