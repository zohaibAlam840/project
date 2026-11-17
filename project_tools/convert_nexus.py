"""Create exact NEXUS tree wrappers for the six supplied PAHG Newick trees.

The Newick tree expression is embedded verbatim. No generic tree writer is used,
because writers may round branch lengths or alter quoted tip labels. Originals
are read only; generated files go in working_copies/.

Run from the project root: py project_tools/convert_nexus.py
Requires: Biopython, DendroPy (see requirements.txt).
"""
from __future__ import annotations

import hashlib
import json
import math
import csv
from pathlib import Path

import dendropy
from Bio import SeqIO

from prepare_inventory import mts_metadata

ROOT = Path(__file__).resolve().parents[1]
WORKING = ROOT / "working_copies"
OUTPUT = ROOT / "inventory" / "nexus_conversion.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_signature(node) -> tuple:
    """Capture topology, tips, branch lengths, support labels, and comments."""
    children = tuple(sorted((tree_signature(child) for child in node.child_node_iter()), key=repr))
    return (
        node.taxon.label if node.taxon is not None else None,
        node.label,
        node.edge.length,
        tuple(node.comments),
        children,
    )


def normalize_label(label: str) -> str:
    return label.strip().replace(" ", "_")


def original_for(tree_file: Path, method: str) -> Path:
    family = tree_file.parent.name.rsplit("_", 1)[-1]
    with (ROOT / "inventory" / "trees.csv").open(encoding="utf-8-sig", newline="") as stream:
        matches = [row for row in csv.DictReader(stream) if row["family"] == family and row["method"] == method]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one inventory source entry for {family} {method}")
    row = matches[0]
    folders = [p for p in (ROOT / "families" / "families").iterdir()
               if p.is_dir() and p.name.startswith(row["candidate_folder_number"] + ".")]
    if len(folders) != 1:
        raise RuntimeError(f"Expected one original family folder for {family}")
    original = folders[0] / row["original_newick"]
    snapshot = ROOT / "original_snapshot" / "families" / folders[0].name / row["original_newick"]
    if not original.is_file() or not snapshot.is_file():
        raise FileNotFoundError(original)
    source_hash = digest(tree_file.read_bytes())
    if digest(original.read_bytes()) != source_hash or digest(snapshot.read_bytes()) != source_hash:
        raise AssertionError(f"Working tree differs from original or snapshot: {tree_file}")
    return original


def convert_one(tree_file: Path, alignment: Path, session: Path) -> dict:
    method = tree_file.stem.rsplit("_", 1)[-1]
    if method not in {"ML", "NJ"}:
        raise ValueError(f"Unrecognized method: {tree_file}")
    original_file = original_for(tree_file, method)
    source_bytes = tree_file.read_bytes()
    tree_text = source_bytes.decode("utf-8-sig").strip()
    if not tree_text.startswith("(") or not tree_text.endswith(";"):
        raise ValueError(f"Expected a single Newick expression: {tree_file}")
    nexus_bytes = (f"#NEXUS\nBEGIN TREES;\n    TREE {method} = " + tree_text + "\nEND;\n").encode("utf-8")
    out_file = tree_file.with_suffix(".nex")
    if out_file.exists() and out_file.read_bytes() != nexus_bytes:
        raise RuntimeError(f"Generated NEXUS already differs; review before overwriting: {out_file}")

    newick = dendropy.Tree.get(path=str(tree_file), schema="newick", preserve_underscores=True)
    nexus = dendropy.Tree.get(data=nexus_bytes.decode("utf-8"), schema="nexus", preserve_underscores=True)
    if tree_signature(newick.seed_node) != tree_signature(nexus.seed_node):
        raise AssertionError(f"NEXUS round trip changed tree contents: {out_file}")
    # This also catches a formatting change to the embedded Newick text.
    embedded = nexus_bytes.decode("utf-8").split(" = ", 1)[1].rsplit("\nEND;", 1)[0]
    if embedded != tree_text:
        raise AssertionError(f"Newick expression was changed: {out_file}")

    tips = [node.taxon.label for node in newick.leaf_node_iter()]
    aligned = list(SeqIO.parse(str(alignment), "fasta"))
    alignment_labels = [normalize_label(record.description) for record in aligned]
    if len(tips) != len(alignment_labels) or len(set(tips)) != len(tips):
        raise AssertionError(f"Leaf count or duplicate label problem: {tree_file}")
    if {normalize_label(x) for x in tips} != set(alignment_labels):
        raise AssertionError(f"Tree leaves do not match alignment: {tree_file}")
    branches = [float(node.edge.length) for node in newick.preorder_node_iter() if node.edge.length is not None]
    if not branches or any(not math.isfinite(x) for x in branches):
        raise AssertionError(f"Invalid or missing branch length: {tree_file}")
    negative_edges = [
        {"label": node.taxon.label if node.taxon is not None else node.label,
         "length": node.edge.length}
        for node in newick.preorder_node_iter()
        if node.edge.length is not None and node.edge.length < 0
    ]
    supports = [float(node.label) for node in newick.preorder_node_iter() if node.label is not None]
    if any(not math.isfinite(x) or x < 0 or x > 1 for x in supports):
        raise AssertionError(f"Unexpected support value outside 0..1: {tree_file}")

    meta = mts_metadata(session)
    expected_method = "Maximum Likelihood" if method == "ML" else "Neighbor-joining"
    if meta["method_in_session"].casefold() != expected_method.casefold():
        raise AssertionError(f"Session method does not match {method}: {session}")
    if not meta["substitution_model"] or not meta["bootstrap_replicates"].isdigit():
        raise AssertionError(f"Missing model or bootstrap metadata: {session}")
    if not out_file.exists():
        out_file.write_bytes(nexus_bytes)
    written_tree = dendropy.Tree.get(path=str(out_file), schema="nexus", preserve_underscores=True)
    if tree_signature(newick.seed_node) != tree_signature(written_tree.seed_node):
        raise AssertionError(f"Written NEXUS file changed the tree: {out_file}")
    return {
        "family": tree_file.parent.name.rsplit("_", 1)[-1],
        "method": method,
        "source_newick": str(tree_file.relative_to(ROOT)).replace("\\", "/"),
        "original_newick": str(original_file.relative_to(ROOT)).replace("\\", "/"),
        "nexus_tree": str(out_file.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": digest(source_bytes),
        "embedded_newick_sha256": digest(tree_text.encode("utf-8")),
        "nexus_sha256": digest(nexus_bytes),
        "tree_leaves": len(tips),
        "alignment_records": len(aligned),
        "branch_count": len(branches),
        "negative_branch_count": len(negative_edges),
        "negative_branches": negative_edges,
        "support_count": len(supports),
        "session_method": meta["method_in_session"],
        "session_model": meta["substitution_model"],
        "session_bootstrap_replicates": int(meta["bootstrap_replicates"]),
        "nexus_roundtrip": "PASS",
        "label_match": "PASS",
        "branch_and_support_range": "REVIEW_NEGATIVE_BRANCH" if negative_edges else "PASS",
        "session_metadata": "PASS",
        "session_tree_comparison": "PENDING",
    }


def main() -> None:
    records = []
    for folder in sorted(WORKING.glob("candidate_*")):
        alignment_files = [p for p in folder.glob("*.fasta") if "align" in p.name.lower()]
        if len(alignment_files) != 1:
            raise RuntimeError(f"Expected one alignment in {folder}")
        for method in ("ML", "NJ"):
            tree_files = list(folder.glob(f"*_{method}.nwk"))
            session_files = list(folder.glob(f"{method} tree.mtsx"))
            if len(tree_files) != 1 or len(session_files) != 1:
                raise RuntimeError(f"Missing or duplicate {method} source files in {folder}")
            records.append(convert_one(tree_files[0], alignment_files[0], session_files[0]))
    if len(records) != 6:
        raise RuntimeError(f"Expected six trees; found {len(records)}")
    OUTPUT.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    for row in records:
        print(row["family"], row["method"], row["tree_leaves"], row["nexus_roundtrip"], row["session_metadata"])


if __name__ == "__main__":
    main()
