"""Join the live PAHG catalogue to the previously captured local file inventory.

The PAHG page identifies families. A name match does not establish that a
particular local FASTA or tree was used for PAHG's published analysis.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if ROOT.name == "project_tools":
    ROOT = ROOT.parent
CATALOGUE = ROOT / "inventory" / "pahg_live_catalogue.json"
INV = ROOT / "inventory"

# Each match was checked against the visible name and link on PAHG's 221-row
# family table. SLC4, COL, ERBB also match the supplied folder names.
PAHG_ID_BY_SYMBOL = {
    "SLC4": 1, "COL": 2, "ERBB": 3,
    "ABLIM": 81, "COL_ALPHA": 92, "CDKN": 163, "DUSP": 99,
    "FZD": 49, "GLI": 4, "GRI": 111, "LAPTM": 71,
    "NFE2": 16, "REEP": 142, "RNF": 202, "SLC26": 148,
    "SH3RF": 160, "S1PR": 176, "WDR62": 235,
}


def csv_rows(name: str) -> list[dict[str, str]]:
    with (INV / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(name: str, rows: list[dict]) -> None:
    with (INV / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    capture = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    assert len(capture["rows"]) == 221
    ids = [int(r["href"].rsplit("/", 1)[-1]) for r in capture["rows"]]
    assert len(set(ids)) == 221
    families = csv_rows("families.csv")
    online = {r["symbol"]: r for r in csv_rows("online_candidates.csv")}
    local = {PAHG_ID_BY_SYMBOL[r["symbol"]]: r for r in families}
    validations = json.loads((INV / "tree_validation.json").read_text(encoding="utf-8"))
    conversions = json.loads((INV / "nexus_conversion.json").read_text(encoding="utf-8"))
    conversion_by_key = {(r["family"], r["method"]): r for r in conversions}
    assert len(conversions) == 6 and all(r["nexus_roundtrip"] == "PASS" for r in conversions)
    validation_by_family = {r["family"]: r for r in validations if r["method"] == "ML"}
    assert len(validations) == 6 and all(v["parse_status"] == v["label_status"] == "PASS" for v in validations)
    assert len(local) == len(families) == 18
    out = []
    for page in capture["rows"]:
        cells = page["cells"]
        assert len(cells) == 5
        fid = int(page["href"].rsplit("/", 1)[-1])
        match = local.get(fid)
        candidate = online.get(match["symbol"]) if match else None
        validation = validation_by_family.get(match["symbol"]) if match else None
        converted = [conversion_by_key[(match["symbol"], method)] for method in ("ML", "NJ")] if validation else []
        negative = sum(r["negative_branch_count"] for r in converted)
        source = "Your files" if match and match["source_type"] == "User supplied" else "PAHG GitHub" if match else "PAHG catalogue"
        raw = match["raw_fasta"] if match else ""
        aligned = match["alignment_fasta"] if match else ""
        if source == "Your files":
            status = "NEXUS round trip passes; branch review" if negative else "NEXUS round trip passes; MEGA review pending"
            next_step = "Review negative COL NJ branch; compare MEGA tree" if negative else "Compare tree with original MEGA analysis"
        elif source == "PAHG GitHub":
            status = "Sequence files only; trees missing"
            next_step = "Verify file pairing and locate original ML/NJ trees"
        else:
            status = "No local research files"
            next_step = "Obtain sequences, alignment and source trees"
        out.append({
            "PAHG ID": fid,
            "Symbol / file key": match["symbol"] if match else "",
            "PAHG family name": cells[0],
            "PAHG year": int(cells[1]) if cells[1].isdigit() else cells[1],
            "PAHG taxa": int(cells[2]) if cells[2].isdigit() else cells[2],
            "PAHG sequences": int(cells[4]) if cells[4].isdigit() else cells[4],
            "Function on PAHG": cells[3],
            "Research file source": source,
            "Raw FASTA": raw,
            "Raw records": int(match["raw_sequence_records"]) if match and match["raw_sequence_records"] else "",
            "Alignment FASTA": aligned,
            "Aligned records": int(match["alignment_sequence_records"]) if match and match["alignment_sequence_records"] else "",
            "Raw/alignment count": candidate["record_count_match"] if candidate else "Same" if source == "Your files" else "",
            "Equal alignment lengths": candidate["alignment_equal_length"] if candidate else "YES" if validation else "",
            "Alignment sites": validation["alignment_length"] if validation else "",
            "Tree leaves": validation["tree_leaves"] if validation else "",
            "ML Newick": "File checks pass" if validation else "Missing",
            "NJ Newick": "File checks pass" if validation else "Missing",
            "Tree NEXUS": "ML + NJ checked" if converted else "Missing",
            "Tree validation": "Round trip + labels pass; MEGA tree pending" if converted else "No tree to validate",
            "Inventory status": status,
            "Next action": next_step,
            "PAHG family page": page["href"],
            "Online source commit": candidate["commit"] if candidate else "",
        })
    assert len(out) == 221
    order = {"Your files": 0, "PAHG GitHub": 1, "PAHG catalogue": 2}
    out.sort(key=lambda r: (order[r["Research file source"]], r["PAHG ID"] if r["Research file source"] == "Your files" else r["PAHG family name"].lower()))
    write_csv("master_221_families.csv", out)
    overview = {
        "catalogue_families": len(out),
        "user_file_families": sum(r["Research file source"] == "Your files" for r in out),
        "github_file_candidates": sum(r["Research file source"] == "PAHG GitHub" for r in out),
        "catalogue_only": sum(r["Research file source"] == "PAHG catalogue" for r in out),
        "recorded_newick_trees": 6,
        "parse_and_label_pass_trees": 6,
        "nexus_roundtrip_pass_trees": 6,
        "negative_branch_trees_for_review": sum(r["negative_branch_count"] > 0 for r in conversions),
        "session_comparison_complete_trees": 0,
        "source": capture["source"],
        "retrieved": capture["retrieved"],
    }
    (INV / "master_221_families.json").write_text(json.dumps({"summary": overview, "rows": out}, indent=2), encoding="utf-8")
    issues = csv_rows("issues.csv")
    for issue in issues:
        if issue["issue"].startswith("Confirm PAHG family ID"):
            issue["status"] = "resolved: official PAHG page matched"
        elif issue["issue"].startswith("Only sequence and alignment FASTA files captured"):
            issue["issue"] = "Obtain source ML/NJ trees and verify that these FASTA files correspond to the PAHG analysis."
        elif issue["family"] == "COL_ALPHA" and issue["issue"] == "Possible overlap with supplied COL family":
            issue["issue"] = "PAHG lists collagen alpha (ID 92) separately from fibrillar collagens (ID 2)."
            issue["status"] = "resolved: distinct PAHG entries"
        elif issue["issue"].startswith("Supplied NEXUS is an alignment"):
            issue["issue"] = "Supplied NEXUS is an alignment; separate, checked ML and NJ NEXUS tree files were created in working_copies."
            issue["status"] = "resolved: tree NEXUS created"
    issues.append({"family": "COL", "method": "NJ", "severity": "review",
                   "issue": "Original NJ tree has a negative branch length (-0.000250018030820602) for Mus_musculus_COL3A1; preserved exactly in NEXUS. Review in MEGA and document interpretation.",
                   "status": "open"})
    online_review = csv_rows("online_candidates.csv")
    for candidate in online_review:
        if candidate["symbol"] == "COL_ALPHA":
            candidate["review_note"] = "Distinct PAHG entry from fibrillar COL; verify file pairing."
    write_csv("review_log_updated.csv", issues)
    (INV / "workbook_data.json").write_text(json.dumps({
        "summary": overview,
        "master": out,
        "trees": csv_rows("trees.csv"),
        "validations": validations,
        "conversions": conversions,
        "online": online_review,
        "issues": issues,
        "sources": csv_rows("source_manifest.csv"),
    }, indent=2), encoding="utf-8")
    print(overview)
    print(Counter(r["Inventory status"] for r in out))


if __name__ == "__main__":
    main()
