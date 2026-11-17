# PAHG MPhil project data inventory

This project tracks all **221 official PAHG gene families**. The source data is
preserved separately from working copies, and every family has an explicit
evidence-based status. Read [DATA_CLEANING_REPORT.md](DATA_CLEANING_REPORT.md)
for the findings and what is still needed.

## Current result (18 November 2026)

| Check | Result |
| --- | ---: |
| Official PAHG family rows | 221 |
| Official FASTA downloads captured | 442 (one raw, one alignment per family) |
| Official alignments incomplete | 121 |
| Equal-length alignments requiring count or pairing review | 32 |
| Datasets passing sequence-level checks | 68 |
| Families with separately supplied ML/NJ Newick trees | 3 (6 trees) |
| Additional PAHG GitHub FASTAs verified against pinned commit | 93 |

The 68 sequence-level passes mean: every aligned record has the same length;
the raw, aligned, and published record counts agree; the multisets of raw and
ungapped aligned protein sequences match exactly; and no raw-format issue was
found. This **does not** validate the published trees or MEGA analyses. PAHG's
download endpoints do not supply source ML/NJ tree files. The six supplied
trees pass parsing, label checks, and exact NEXUS round trips, but still need
comparison to their original MEGA analyses. The COL NJ tree retains one
negative branch length for review.

## Files

- `families/` and `families.zip`: user-supplied originals, unchanged.
- `original_snapshot/`: preserved copies and SHA256 provenance.
- `online_sources/PAHG_live_2026-11-18/`: 442 official PAHG download responses,
  named by confirmed family ID. Do not edit these.
- `online_sources/PAHG_GitHub_83e042106746/`: all 93 public FASTAs from pinned
  PAHG GitHub commit `83e0421067465e6855371fb65f99384855d23d80`, checked
  against Git blob hashes. These are supplemental source evidence.
- `working_copies/pahg_live_fastas/`: official FASTA working copies. Twelve
  missing header line breaks were inserted and three text preambles removed;
  the source downloads remain unchanged.
- `working_copies/public_fastas/`: GitHub FASTA working copies. Twenty-eight
  missing header line breaks were inserted; source files remain unchanged.
- `working_copies/candidate_*`: six NEXUS tree copies and supplied-family
  working files.
- `inventory/PAHG_master_inventory.xlsx`: readable master workbook, also
  delivered under `outputs/2026-11-18-data-cleaning/`.
- `inventory/master_221_families.csv` and `.json`: machine-readable master.
- `inventory/pahg_live_audit.csv` and `.json`: per-family download, count,
  alignment, sequence-pairing, issue, and SHA256 checks.
- `inventory/pairing_review_details.csv` and `.json`: the specific records
  requiring review in the 32 equal-length but discordant datasets.
- `inventory/pahg_live_download_manifest.json`: download URL, date, path,
  status, byte size, and hash for each official response.
- `inventory/public_fasta_audit.csv` and `.json`: all 93 GitHub FASTA checks.

## Rebuild

The scripts run from the project root. The download scripts are resumable and
reuse verified local captures.

```powershell
py -m pip install -r requirements.txt
py project_tools/fetch_public_fastas.py
py project_tools/normalize_public_fastas.py
py project_tools/audit_public_fastas.py
py project_tools/fetch_pahg_live.py
py project_tools/audit_pahg_live.py
py project_tools/review_pahg_pairing.py
py project_tools/validate_supplied_trees.py
py project_tools/convert_nexus.py
py project_tools/build_full_inventory.py
node project_tools/build_workbook.mjs
```

`build_workbook.mjs` uses the Codex bundled `@oai/artifact-tool` runtime. The
existing `project_tools/node_modules` link points to that runtime. Do not
commit changes inside that dependency link.

## Sources

- [PAHG family table](https://www.pahgncb.com/genomedb/public/genefamilies)
- [PAHG downloads](https://www.pahgncb.com/genomedb/public/downloads)
- [PAHG GitHub repository](https://github.com/PAHG-Database/PAHG/tree/83e0421067465e6855371fb65f99384855d23d80/public)
- [PAHG publication](https://pmc.ncbi.nlm.nih.gov/articles/PMC12522930/)
