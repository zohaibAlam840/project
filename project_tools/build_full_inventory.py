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

# Clear name matches to official table entries. These repository files contain
# raw sequences only; they are candidate inputs, not validated PAHG analyses.
RAW_ONLY = {
    83: ("ADAM", "adam metallopeptidase domain (adam).fasta"),
    89: ("ARAP", "arfgap(ankyrin repeat and ph domain) (arap).fasta"),
    14: ("CBX", "chromobox homolog.fasta"),
    168: ("FUBP", "far upstream element (fuse) binding protein family.fasta"),
    29: ("FMNL", "formin-like.fasta"),
    112: ("GRK", "g protein-coupled receptor kinase (grk).fasta"),
    5: ("HH", "hedgehog family.fasta"),
    31: ("HDAC", "histone deacetylase.fasta"),
    236: ("HR", "hr gene family .fasta"),
    6: ("INH", "inhibin.fasta"),
    7: ("IGFBP", "insulin-like growth factor-binding protein.fasta"),
    74: ("MYC", "myc proto-oncogene protein.fasta"),
    55: ("MYO1", "myosin 1.fasta"),
    134: ("PITX", "pituitary homeobox (pitx).fasta"),
    144: ("RHO", "ras homolog family (rho).fasta"),
    63: ("SLC38", "solute carrier family 38a.fasta"),
    173: ("SH", "src homology 2 domain containing adaptor protein.fasta"),
    41: ("TNS", "tensin.fasta"),
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
    online_audit = {r["symbol"]: r for r in json.loads((INV / "online_family_audit.json").read_text(encoding="utf-8"))}
    public_audit = {r["filename"]: r for r in json.loads((INV / "public_fasta_audit.json").read_text(encoding="utf-8"))}
    normalized = {r["filename"]: r for r in json.loads((INV / "public_fasta_normalization.json").read_text(encoding="utf-8"))}
    live_rows = json.loads((INV / "pahg_live_audit.json").read_text(encoding="utf-8"))
    live_by_id = {r["pahg_id"]: r for r in live_rows}
    assert len(live_by_id) == len(live_rows) == 221
    conversion_by_key = {(r["family"], r["method"]): r for r in conversions}
    assert len(conversions) == 6 and all(r["nexus_roundtrip"] == "PASS" for r in conversions)
    validation_by_family = {r["family"]: r for r in validations if r["method"] == "ML"}
    assert len(validations) == 6 and all(v["parse_status"] == v["label_status"] == "PASS" for v in validations)
    assert len(local) == len(families) == 18
    assert len(RAW_ONLY) == 18 and not (set(RAW_ONLY) & set(local))
    out = []
    for page in capture["rows"]:
        cells = page["cells"]
        assert len(cells) == 5
        fid = int(page["href"].rsplit("/", 1)[-1])
        match = local.get(fid)
        candidate = online.get(match["symbol"]) if match else None
        raw_only = RAW_ONLY.get(fid)
        audited = online_audit.get(match["symbol"]) if candidate else None
        validation = validation_by_family.get(match["symbol"]) if match else None
        converted = [conversion_by_key[(match["symbol"], method)] for method in ("ML", "NJ")] if validation else []
        negative = sum(r["negative_branch_count"] for r in converted)
        source = "Your files" if match and match["source_type"] == "User supplied" else "PAHG GitHub alignment" if candidate else "PAHG GitHub raw only" if raw_only else "PAHG catalogue"
        raw = match["raw_fasta"] if match else raw_only[1] if raw_only else ""
        aligned = match["alignment_fasta"] if match else ""
        public_raw = normalized.get(raw) if source != "Your files" else None
        raw_records = int(match["raw_sequence_records"]) if match and match["raw_sequence_records"] else public_raw["working_records"] if public_raw else ""
        if source == "Your files":
            status = "NEXUS round trip passes; branch review" if negative else "NEXUS round trip passes; MEGA review pending"
            next_step = "Review negative COL NJ branch; compare MEGA tree" if negative else "Compare tree with original MEGA analysis"
        elif source == "PAHG GitHub alignment":
            status = "Source alignment incomplete" if audited["readiness"] == "SOURCE INCOMPLETE" else "Alignment format passes; trees missing"
            next_step = "Obtain untruncated alignment and source ML/NJ trees" if audited["readiness"] == "SOURCE INCOMPLETE" else "Verify analysis provenance and obtain source ML/NJ trees"
        elif source == "PAHG GitHub raw only":
            status = "Raw sequences only; alignment and trees missing"
            next_step = "Verify PAHG analysis linkage; obtain alignment and source trees"
        else:
            status = "No local research files"
            next_step = "Obtain sequences, alignment and source trees"
        out.append({
            "PAHG ID": fid,
            "Symbol / file key": match["symbol"] if match else raw_only[0] if raw_only else "",
            "PAHG family name": cells[0],
            "PAHG year": int(cells[1]) if cells[1].isdigit() else cells[1],
            "PAHG taxa": int(cells[2]) if cells[2].isdigit() else cells[2],
            "PAHG sequences": int(cells[4]) if cells[4].isdigit() else cells[4],
            "Function on PAHG": cells[3],
            "Research file source": source,
            "Raw FASTA": raw,
            "Raw records": raw_records,
            "Alignment FASTA": aligned,
            "Aligned records": int(match["alignment_sequence_records"]) if match and match["alignment_sequence_records"] else "",
            "Raw/alignment count": candidate["record_count_match"] if candidate else "Same" if source == "Your files" else "",
            "Equal alignment lengths": audited["equal_alignment_lengths"] if audited else "YES" if validation else "",
            "Alignment sites": validation["alignment_length"] if validation else audited["alignment_sites_max"] if audited else "",
            "Shortest aligned record": audited["alignment_sites_min"] if audited else validation["alignment_length"] if validation else "",
            "Source limit flag": audited["possible_source_truncation"] if audited else "",
            "Header line breaks repaired": normalized[aligned]["inserted_header_line_breaks"] if aligned in normalized else public_raw["inserted_header_line_breaks"] if public_raw else "",
            "Raw sequences found in alignment": audited["exact_ungapped_sequence_matches"] if audited else "",
            "Tree leaves": validation["tree_leaves"] if validation else "",
            "ML Newick": "File checks pass" if validation else "Missing",
            "NJ Newick": "File checks pass" if validation else "Missing",
            "Tree NEXUS": "ML + NJ checked" if converted else "Missing",
            "Tree validation": "Round trip + labels pass; MEGA tree pending" if converted else "No tree to validate",
            "Inventory status": status,
            "Next action": next_step,
            "PAHG family page": page["href"],
            "Online source commit": "83e0421067465e6855371fb65f99384855d23d80" if source.startswith("PAHG GitHub") else "",
            "Working FASTA path": normalized[aligned]["working_path"] if aligned in normalized else public_raw["working_path"] if public_raw else "",
        })
    assert len(out) == 221
    for row in out:
        fid = row["PAHG ID"]
        live = live_by_id[fid]
        previous_source = row["Research file source"]
        row["GitHub source evidence"] = ("Alignment + raw or alignment only" if previous_source == "PAHG GitHub alignment"
                                         else "Raw only" if previous_source == "PAHG GitHub raw only" else "")
        row["Official raw source"] = f"online_sources/PAHG_live_2026-11-18/{fid:04d}_sequence.fasta"
        row["Official alignment source"] = f"online_sources/PAHG_live_2026-11-18/{fid:04d}_alignment.fasta"
        row["Official raw SHA256"] = live["raw_sha256"]
        row["Official alignment SHA256"] = live["alignment_sha256"]
        row["Official raw records"] = live["raw_records"]
        row["Official aligned records"] = live["alignment_records"]
        row["Official alignment status"] = live["inventory_status"]
        row["Official exact sequence matches"] = live["exact_ungapped_sequence_matches"]
        row["Official alignment issues"] = live["alignment_issues"]
        row["Official raw issues"] = live["raw_issues"]
        if previous_source == "Your files":
            continue
        row["Research file source"] = "PAHG official download"
        row["Raw FASTA"] = f"{fid:04d}_sequence.fasta"
        row["Raw records"] = live["raw_records"]
        row["Alignment FASTA"] = f"{fid:04d}_alignment.fasta"
        row["Aligned records"] = live["alignment_records"]
        row["Raw/alignment count"] = "YES" if live["raw_records"] == live["alignment_records"] else "NO"
        row["Equal alignment lengths"] = live["alignment_equal_lengths"]
        row["Alignment sites"] = live["alignment_max_length"]
        row["Shortest aligned record"] = live["alignment_min_length"]
        row["Source limit flag"] = "YES" if "65,535-byte" in live["alignment_issues"] or live["alignment_bytes"] == 65535 else "NO"
        row["Header line breaks repaired"] = live["alignment_header_repairs"] + live["raw_header_repairs"]
        row["Raw sequences found in alignment"] = live["exact_ungapped_sequence_matches"]
        row["Working FASTA path"] = live["alignment_working_path"]
        row["Inventory status"] = live["inventory_status"]
        row["Next action"] = ("Obtain full source alignment or create a documented new alignment from raw sequences; obtain original trees"
                              if live["inventory_status"] == "SOURCE ALIGNMENT INCOMPLETE"
                              else "Resolve record/sequence discrepancy; obtain original trees"
                              if live["inventory_status"] == "FORMAT OR PAIRING REVIEW"
                              else "Obtain original ML/NJ trees; verify analysis method and labels")
    assert sum(r["Research file source"] == "PAHG official download" for r in out) == 218
    order = {"Your files": 0, "PAHG official download": 1}
    out.sort(key=lambda r: (order[r["Research file source"]], r["PAHG ID"] if r["Research file source"] == "Your files" else r["PAHG family name"].lower()))
    write_csv("master_221_families.csv", out)
    overview = {
        "catalogue_families": len(out),
        "user_file_families": sum(r["Research file source"] == "Your files" for r in out),
        "github_alignment_candidates": sum(r["GitHub source evidence"] == "Alignment + raw or alignment only" for r in out),
        "github_raw_only_candidates": sum(r["GitHub source evidence"] == "Raw only" for r in out),
        "official_download_families": len(live_rows),
        "official_fasta_files": len(live_rows) * 2,
        "official_incomplete_alignments": sum(r["inventory_status"] == "SOURCE ALIGNMENT INCOMPLETE" for r in live_rows),
        "official_pairing_review": sum(r["inventory_status"] == "FORMAT OR PAIRING REVIEW" for r in live_rows),
        "official_sequence_checks_pass": sum(r["inventory_status"] == "SEQUENCE CHECKS PASS; PAHG TREE DOWNLOAD UNAVAILABLE" for r in live_rows),
        "official_header_repairs": sum(r["alignment_header_repairs"] + r["raw_header_repairs"] for r in live_rows),
        "public_fastas_verified": len(public_audit),
        "public_fasta_header_repairs": sum(r["inserted_header_line_breaks"] for r in normalized.values()),
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
    issues.extend([
        {"family": "ALL", "method": "All", "severity": "source incomplete",
         "issue": "121 of 221 official PAHG alignment downloads are incomplete: 120 end with a shortened final record and one reaches 65,535 bytes with records missing. Do not pad or present these as full source alignments.", "status": "open"},
        {"family": "ALL", "method": "All", "severity": "pairing review",
         "issue": "32 official alignments have equal-length records but fail at least one published-count, raw-sequence, or raw-format consistency check.", "status": "open"},
        {"family": "ALL", "method": "All", "severity": "trees missing",
         "issue": "68 official family datasets pass alignment format, sequence-count and exact ungapped-sequence checks; PAHG does not provide source ML/NJ tree downloads. Six trees were supplied separately for three of these families.", "status": "open"},
    ])
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
        "online_audit": list(online_audit.values()),
        "live_audit": live_rows,
        "pairing_review": json.loads((INV / "pairing_review_details.json").read_text(encoding="utf-8")),
        "public_audit": list(public_audit.values()),
        "normalization": list(normalized.values()),
        "issues": issues,
        "sources": csv_rows("source_manifest.csv"),
    }, indent=2), encoding="utf-8")
    print(overview)
    print(Counter(r["Inventory status"] for r in out))


if __name__ == "__main__":
    main()
