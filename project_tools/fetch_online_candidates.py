"""Fetch pinned PAHG GitHub sequence and alignment pairs for the pilot.

Files are immutable once captured. These are candidate families with sequence
material, not validated PAHG tree exports.
"""
from __future__ import annotations
import csv
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "83e0421067465e6855371fb65f99384855d23d80"
BASE = f"https://raw.githubusercontent.com/PAHG-Database/PAHG/{COMMIT}/public/"
DEST = ROOT / "online_sources" / f"PAHG_GitHub_{COMMIT[:12]}"
TREE_FILE = ROOT / "project_tools" / "repo_tree.json"
CANDIDATES = [
    ("ABLIM", "Actin binding LIM protein", "actin bnding lim protein (ablim).fasta", "actin bnding lim protein (ablim)Alignment.fasta", ""),
    ("COL_ALPHA", "Collagen alpha", "collagen alpha (col).fasta", "collagen alpha (col)Alignment.fasta", "Possible overlap with supplied COL family"),
    ("CDKN", "Cyclin dependent kinase inhibitor", "", "cyclin-dependent kinase inhibitor familyAlignment.fasta", ""),
    ("DUSP", "Dual specificity phosphatase", "dual specificity phosphatase (dusp).fasta", "dual specificity phosphatase (dusp)Alignment.fasta", ""),
    ("FZD", "Frizzled", "frizzled.fasta", "frizzledAlignment.fasta", ""),
    ("GLI", "GLI zinc finger protein", "gli zinc-finger protein family.fasta", "gli zinc-finger protein familyAlignment.fasta", ""),
    ("GRI", "Glutamate receptor ionotropic", "", "glutamate receptor ionotropic (gri)Alignment.fasta", ""),
    ("LAPTM", "Lysosomal associated transmembrane protein", "lysosomal-associated transmembrane protein.fasta", "lysosomal-associated transmembrane proteinAlignment.fasta", ""),
    ("NFE2", "Nuclear factor erythroid derived 2", "", "nuclear factor (erythroid-derived 2)Alignment.fasta", ""),
    ("REEP", "Receptor expression enhancing protein", "", "receptor expression-enhancing proteinAlignment.fasta", ""),
    ("RNF", "Ring finger protein subfamily 2", "ring finger protein subfamily 2.fasta", "ring finger protein subfamily 2Alignment.fasta", ""),
    ("SLC26", "Solute carrier family 26", "solute carrier family 26 (slc26a).fasta", "solute carrier family 26 (slc26a)Alignment.fasta", ""),
    ("SH3RF", "Sorbin and SH3 domain containing", "", "sorbin and sh3 domain containing (sh3rf)Alignment.fasta", ""),
    ("S1PR", "Sphingosine 1 phosphate receptor", "", "sphingosine-1-phosphate receptorAlignment.fasta", ""),
    ("WDR62", "WDR domain 62", "wdr domain 62.fasta", "wdr domain 62Alignment.fasta", ""),
]

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

GIT_BLOBS = {item["path"]: item["sha"] for item in json.loads(TREE_FILE.read_text(encoding="utf-8"))["tree"] if item["type"] == "blob"}

def count_records(data: bytes) -> int:
    return sum(line.startswith(b">") for line in data.splitlines())

def alignment_lengths(data: bytes) -> set[int]:
    records = data.decode("utf-8-sig", "replace").split(">")
    return {len("".join(r.splitlines()[1:])) for r in records[1:]}

def fetch(name: str) -> dict:
    url = BASE + urllib.parse.quote(name)
    dest = DEST / name
    if dest.exists():
        data = dest.read_bytes()
    else:
        req = urllib.request.Request(url, headers={"User-Agent":"PAHG-MPhil-pilot-inventory"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
        if not data.startswith(b">"):
            raise RuntimeError(f"Unexpected FASTA content from {url}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    expected = GIT_BLOBS.get("public/" + name)
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if not expected or actual != expected:
        raise RuntimeError(f"File does not match pinned GitHub commit: {dest}")
    return {"filename":name,"source_url":url,"local_path":str(dest.relative_to(ROOT)),
            "sha256":digest(data),"bytes":len(data),"records":count_records(data),
            "distinct_record_lengths":len(alignment_lengths(data))}

def main() -> None:
    rows=[]
    for symbol,name,raw,aligned,note in CANDIDATES:
        raw_info=fetch(raw) if raw else None
        aligned_info=fetch(aligned)
        raw_count=raw_info["records"] if raw_info else ""
        count_match=(raw_count == aligned_info["records"]) if raw_info else False
        rows.append({"symbol":symbol,"family_name_candidate":name,"official_pahg_id":"",
                     "id_status":"UNCONFIRMED","source":"PAHG public GitHub repository",
                     "commit":COMMIT,"raw_fasta":raw,"alignment_fasta":aligned,
                     "raw_records":raw_count,"alignment_records":aligned_info["records"],
                     "alignment_equal_length":"YES" if aligned_info["distinct_record_lengths"]==1 else "NO",
                     "record_count_match":"YES" if count_match else "NO" if raw_info else "RAW FILE MISSING",
                     "pair_status":"NEEDS REVIEW" if not count_match or aligned_info["distinct_record_lengths"]!=1 or note else "COUNT CHECK PASSED",
                     "ml_session":"","nj_session":"","ml_newick":"","nj_newick":"",
                     "tree_status":"SOURCE TREE FILES NOT FOUND IN REPOSITORY",
                     "raw_url":raw_info["source_url"] if raw_info else "","alignment_url":aligned_info["source_url"],
                     "raw_sha256":raw_info["sha256"] if raw_info else "","alignment_sha256":aligned_info["sha256"],
                     "review_note":note})
    out=ROOT/"inventory"; out.mkdir(exist_ok=True)
    with (out/"online_candidates.csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (out/"online_candidates.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
    print(f"Captured {len(rows)} candidate alignments and {sum(bool(r['raw_fasta']) for r in rows)} raw FASTA files from PAHG commit {COMMIT}")

if __name__ == "__main__":
    main()
