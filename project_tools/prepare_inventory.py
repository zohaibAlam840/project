"""Preserve supplied PAHG files and refresh a source-based pilot inventory.

Run: python project_tools/prepare_inventory.py
The snapshot is immutable: if a supplied file changes after first capture, stop
and review it rather than overwriting the captured copy.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "families" / "families"
SNAPSHOT = ROOT / "original_snapshot"
WORKING = ROOT / "working_copies"
RESULTS = ROOT / "inventory"
FAMILIES = {
    "SLC4": ("1.Solute carrier family 4 (SLC4)", "Solute carrier family 4"),
    "COL": ("2. fibrillar collagens (COL)", "Fibrillar collagens"),
    "ERBB": ("3.Erb-b2 receptor tyrosine kinases (ERBB)", "Erb-b2 receptor tyrosine kinases"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def preserve(src: Path, relative: Path) -> dict:
    dst = SNAPSHOT / relative
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if sha256(src) != sha256(dst):
            raise RuntimeError(f"Source differs from preserved snapshot: {src}")
    else:
        shutil.copy2(src, dst)
    return {"source_path": str(src.relative_to(ROOT)), "snapshot_path": str(dst.relative_to(ROOT)),
            "bytes": src.stat().st_size, "sha256": sha256(src)}


def mts_metadata(path: Path) -> dict:
    # MTSX is a binary format containing a readable analysis-settings segment.
    text = path.read_bytes().decode("latin1", errors="ignore")
    out = {}
    for key, label in [
        ("method_in_session", "Statistical Method"),
        ("substitution_model", "Model/Method"),
        ("bootstrap_replicates", "Bootstrap Replicates"),
        ("substitutions_type", "Substitutions Type"),
        ("rates_among_sites", "Rates among Sites"),
        ("gaps_missing_data", "Gaps/Missing Data"),
    ]:
        m = re.search(r"(?:^|[,\" ])\s*" + re.escape(label) + r"\s*=\s*([^\",\r\n]+)", text)
        out[key] = m.group(1).strip() if m else ""
    return out


def fasta_count(path: Path) -> int:
    return sum(line.startswith(b">") for line in path.read_bytes().splitlines())


def nexus_kind(path: Path) -> str:
    text = path.read_text(errors="replace")
    blocks = {x.lower() for x in re.findall(r"\bbegin\s+(\w+)\s*;", text, re.I)}
    return "tree" if "trees" in blocks else "alignment" if "characters" in blocks else "unknown"


def choose(files: list[Path], method: str, extension: str) -> Path | None:
    found = [p for p in files if p.name.lower().startswith(method.lower()) and p.suffix.lower() == extension] if extension == ".mtsx" else [p for p in files if re.search(rf"_{method}\.nwk(?:\.nwk)?$", p.name, re.I)]
    if len(found) > 1:
        raise RuntimeError(f"Ambiguous {method} {extension}: {found}")
    return found[0] if found else None


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    if not SOURCE.is_dir():
        raise FileNotFoundError(SOURCE)
    RESULTS.mkdir(exist_ok=True)
    manifest = []
    for src in sorted(SOURCE.rglob("*")):
        if src.is_file():
            manifest.append(preserve(src, Path("families") / src.relative_to(SOURCE)))
    archive = ROOT / "families.zip"
    if archive.exists():
        manifest.append(preserve(archive, Path("families.zip")))

    family_rows, tree_rows, issue_rows = [], [], []
    for symbol, (folder, family_name) in FAMILIES.items():
        family_dir = SOURCE / folder
        files = list(family_dir.iterdir())
        number = re.match(r"\d+", folder).group()
        fasta = [p for p in files if p.suffix.lower() == ".fasta"]
        aligned = [p for p in fasta if "align" in p.stem.lower()]
        raw = [p for p in fasta if p not in aligned]
        nexus = [p for p in files if p.suffix.lower() == ".nex"]
        work_dir = WORKING / f"candidate_{number}_{symbol}"
        work_dir.mkdir(parents=True, exist_ok=True)
        for src in files:
            if src.suffix.lower() == ".nwk":
                method_match = re.search(r"_(ML|NJ)\.nwk(?:\.nwk)?$", src.name, re.I)
                name = f"candidate_{number}_{symbol}_{method_match.group(1).upper()}.nwk" if method_match else src.name
            else:
                name = src.name
            dst = work_dir / name
            if dst.exists() and sha256(dst) != sha256(src):
                raise RuntimeError(f"Working copy differs from source; review before replacing: {dst}")
            if not dst.exists():
                shutil.copy2(src, dst)
        family_rows.append({
            "candidate_folder_number": number, "confirmed_pahg_id": "", "id_status": "UNCONFIRMED",
            "family_name_from_folder": family_name, "symbol": symbol,
            "raw_fasta": raw[0].name if len(raw) == 1 else "",
            "alignment_fasta": aligned[0].name if len(aligned) == 1 else "",
            "raw_sequence_records": fasta_count(raw[0]) if len(raw) == 1 else "",
            "alignment_sequence_records": fasta_count(aligned[0]) if len(aligned) == 1 else "",
            "nexus_supplied": nexus[0].name if len(nexus) == 1 else "",
            "nexus_supplied_kind": nexus_kind(nexus[0]) if len(nexus) == 1 else "",
            "working_folder": str(work_dir.relative_to(ROOT)),
            "paralogon": "", "published_tree_image": "", "family_status": "Inventory complete; validation pending",
            "source_type": "User supplied", "source_commit": "",
        })
        issue_rows.append({"family": symbol, "method": "", "severity": "review", "issue": "Confirm PAHG family ID; folder number is only a candidate.", "status": "open"})
        if nexus and nexus_kind(nexus[0]) != "tree":
            issue_rows.append({"family": symbol, "method": "", "severity": "gap", "issue": "Supplied NEXUS is an alignment; NEXUS tree files remain to be created.", "status": "open"})
        for method in ("ML", "NJ"):
            session = choose(files, method, ".mtsx")
            nwk = choose(files, method, ".nwk")
            meta = mts_metadata(session) if session else {}
            working_nwk = f"candidate_{number}_{symbol}_{method}.nwk" if nwk else ""
            tree_rows.append({
                "candidate_folder_number": number, "confirmed_pahg_id": "", "family": symbol, "method": method,
                "source_session": session.name if session else "", "alignment_fasta": aligned[0].name if len(aligned) == 1 else "",
                "original_newick": nwk.name if nwk else "", "working_newick": working_nwk,
                "nexus_tree": "", "newick_exists": "YES" if nwk else "NO", "nexus_tree_exists": "NO",
                "parse_validation": "PENDING", "label_validation": "PENDING", "source_comparison": "PENDING",
                "substitution_model": meta.get("substitution_model", ""),
                "bootstrap_replicates": meta.get("bootstrap_replicates", ""),
                "substitutions_type": meta.get("substitutions_type", ""),
                "rates_among_sites": meta.get("rates_among_sites", ""),
                "gaps_missing_data": meta.get("gaps_missing_data", ""),
                "mega_version": "", "source_publication": "", "release_status": "NOT READY",
            })
            if nwk and nwk.name.lower().endswith(".nwk.nwk"):
                issue_rows.append({"family": symbol, "method": method, "severity": "naming", "issue": "Original Newick has double .nwk extension; working copy has standard name.", "status": "working copy named"})
            if not session or not nwk:
                issue_rows.append({"family": symbol, "method": method, "severity": "gap", "issue": "Missing source session or Newick file.", "status": "open"})
    online_path = RESULTS / "online_candidates.json"
    online_rows = json.loads(online_path.read_text(encoding="utf-8")) if online_path.exists() else []
    for item in online_rows:
        family_rows.append({
            "candidate_folder_number": "", "confirmed_pahg_id": "", "id_status": "UNCONFIRMED",
            "family_name_from_folder": item["family_name_candidate"], "symbol": item["symbol"],
            "raw_fasta": item["raw_fasta"], "alignment_fasta": item["alignment_fasta"],
            "raw_sequence_records": item["raw_records"], "alignment_sequence_records": item["alignment_records"],
            "nexus_supplied": "", "nexus_supplied_kind": "", "working_folder": "",
            "paralogon": "", "published_tree_image": "",
            "family_status": "Online alignment only; raw sequences and trees missing" if not item["raw_fasta"] else "Online sequence and alignment need review; trees missing",
            "source_type": "PAHG public GitHub", "source_commit": item["commit"],
        })
        issue_rows.append({"family": item["symbol"], "method": "", "severity": "gap",
                           "issue": "Only sequence and alignment FASTA files captured; obtain matching PAHG source tree files and confirm family ID.",
                           "status": "open"})
        if item["record_count_match"] == "NO":
            issue_rows.append({"family": item["symbol"], "method": "", "severity": "review",
                               "issue": "Raw FASTA and alignment FASTA have different sequence-record counts; confirm they belong to the same analysis dataset.",
                               "status": "open"})
        if item["record_count_match"] == "RAW FILE MISSING":
            issue_rows.append({"family": item["symbol"], "method": "", "severity": "gap",
                               "issue": "No matching raw family FASTA file was found in the repository snapshot.",
                               "status": "open"})
        if item["alignment_equal_length"] == "NO":
            issue_rows.append({"family": item["symbol"], "method": "", "severity": "review",
                               "issue": "Alignment FASTA records have different lengths; inspect alignment structure and suitability.",
                               "status": "open"})
        if item.get("review_note"):
            issue_rows.append({"family": item["symbol"], "method": "", "severity": "review",
                               "issue": item["review_note"], "status": "open"})
    write_csv(RESULTS / "families.csv", family_rows, list(family_rows[0]))
    write_csv(RESULTS / "trees.csv", tree_rows, list(tree_rows[0]))
    write_csv(RESULTS / "issues.csv", issue_rows, list(issue_rows[0]))
    write_csv(RESULTS / "source_manifest.csv", manifest, list(manifest[0]))
    (RESULTS / "source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (RESULTS / "inventory_data.json").write_text(json.dumps({
        "Families": family_rows, "Trees": tree_rows, "Issues": issue_rows,
        "Online candidates": online_rows,
        "Source files": manifest,
    }, indent=2), encoding="utf-8")
    print(f"Preserved {len(manifest)} source files; inventoried {len(family_rows)} families and {len(tree_rows)} trees.")
    print(f"Snapshot: {SNAPSHOT}\nWorking copies: {WORKING}\nInventory: {RESULTS}")


if __name__ == "__main__":
    main()
