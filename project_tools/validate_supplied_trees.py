"""Parse the six supplied Newick trees and compare tip labels to alignments.

Requires Biopython (tested with 1.87). The original files are read only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from Bio import Phylo, SeqIO

PROJECT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
OUT = PROJECT / "inventory" / "tree_validation.json"


def normalize(label: str) -> str:
    return label.strip().replace(" ", "_")


def main() -> None:
    results = []
    for folder in sorted((PROJECT / "working_copies").glob("candidate_*")):
        aligned = next(p for p in folder.glob("*.fasta") if "align" in p.name.lower())
        sequences = list(SeqIO.parse(str(aligned), "fasta"))
        align_labels = [normalize(s.description) for s in sequences]
        lengths = [len(s.seq) for s in sequences]
        for tree_file in sorted(folder.glob("*.nwk")):
            method = tree_file.stem.rsplit("_", 1)[-1]
            tree = Phylo.read(str(tree_file), "newick")
            tip_labels = [normalize(t.name or "") for t in tree.get_terminals()]
            missing = sorted(set(align_labels) - set(tip_labels))
            extra = sorted(set(tip_labels) - set(align_labels))
            result = {
                "family": folder.name.rsplit("_", 1)[-1],
                "method": method,
                "tree_file": tree_file.name,
                "alignment_file": aligned.name,
                "tree_leaves": len(tip_labels),
                "alignment_records": len(align_labels),
                "alignment_length": lengths[0] if len(set(lengths)) == 1 else "",
                "alignment_equal_length": len(set(lengths)) == 1,
                "duplicate_tree_labels": len(tip_labels) - len(set(tip_labels)),
                "duplicate_alignment_labels": len(align_labels) - len(set(align_labels)),
                "missing_from_tree": missing,
                "extra_in_tree": extra,
                "parse_status": "PASS",
                "label_status": "PASS" if not missing and not extra and len(tip_labels) == len(align_labels) else "REVIEW",
            }
            results.append(result)
    if len(results) != 6:
        raise RuntimeError(f"Expected six Newick trees; found {len(results)}")
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    for x in results:
        print(x["family"], x["method"], x["tree_leaves"], x["parse_status"], x["label_status"], x["alignment_equal_length"])


if __name__ == "__main__":
    main()
