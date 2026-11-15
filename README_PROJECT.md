# PAHG MPhil project inventory

The master workbook now lists **all 221 families in the live PAHG family table**. It is a catalogue and research progress tracker. A family appearing in the catalogue does not mean its analysis files or downloadable trees are available locally.

## What the workbook shows

- **Master inventory:** 221 PAHG IDs and names, year, taxa, published sequence count, function, local file source, FASTA counts, alignment checks, tree availability, validation state, and next action. The three families with your files appear first, then the 15 GitHub candidates, then the 203 catalogue-only entries.
- **Tree files:** the six supplied ML/NJ Newick files, MEGA sessions and analysis settings, alignment size, parse and leaf-label checks, and the outstanding source comparison.
- **Online data:** the 15 public GitHub file candidates, URLs, pinned commit hashes, record counts, and quality flags.
- **Review log:** specific gaps and checks. PAHG ID matching for the supplied families is resolved; file-to-analysis linkage for online candidates still requires review.
- **Original files:** the earlier SHA256 manifest for your original files and their preserved copies.
- **How to read:** plain-language definitions and sources.

## Current evidence

PAHG's live family table lists 221 entries. Your folder names match PAHG SLC4 **ID 1**, fibrillar collagens **ID 2**, and ERBB **ID 3**. We located 15 other name-matched candidate families in the public [PAHG GitHub repository](https://github.com/PAHG-Database/PAHG) at commit `83e0421067465e6855371fb65f99384855d23d80`. These have alignments; nine have matching-name raw FASTA files. The GitHub FASTA files need pairing and provenance review before being treated as the exact published analysis datasets. The other 203 families currently have catalogue metadata only in this workspace.

The six supplied Newick trees all parse. Each has the same number of leaves as its associated alignment (37 SLC4, 40 COL, 29 ERBB), and the tip-label sets match after normalizing spaces to underscores. All three supplied alignments have equal-length records. **This is a file-level check, not a scientific verification of topology, branch lengths, model choice, bootstrap values, or the MEGA sessions.** The supplied `.nex` files contain alignments; NEXUS *tree* exports remain missing. A trial conversion with Biopython's generic NEXUS writer lost branch-length precision and had trouble reading labels containing parentheses, so it was not used for the deliverable.

## Files and provenance

- `families/families/`, `families.zip`: your originals; left unchanged.
- `original_snapshot/`: preserved copies of your original files.
- `working_copies/`: standardized names for the supplied files; tree content unchanged.
- `online_sources/`: public GitHub FASTA candidates, separate from your files.
- `inventory/pahg_live_catalogue.json`: captured 221-row PAHG table, source URL, and retrieval date (2026-11-15).
- `inventory/master_221_families.csv` and `.json`: machine-readable master records.
- `inventory/tree_validation.json`: six parse and label-check results.
- `inventory/PAHG_master_inventory.xlsx`: formatted workbook.

The live table's per-family sequence counts are copied as shown on 2026-11-15. They are not the same measure as the record counts in a local FASTA file. The live rows currently sum to 15,389, whereas the 2025 [PAHG paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12522930/) reports 15,231 sequences; a database update or definition difference may explain this, but that has not been established.

## Rebuild the workbook

From the project root, run the scripts in this order:

```powershell
py project_tools/validate_supplied_trees.py
py project_tools/build_full_inventory.py
node project_tools/build_workbook.mjs
py project_tools/polish_workbook.py
```

`validate_supplied_trees.py` requires Biopython. The workbook builder requires `@oai/artifact-tool` (the current `project_tools/node_modules` junction points to the Codex bundled runtime). The capture in `inventory/pahg_live_catalogue.json` keeps this build reproducible without refetching PAHG. To capture a newer PAHG release, recrawl the official table and rerun the build, checking IDs and file-name matches again.

## Next research work

1. Export exact NEXUS trees while preserving the original Newick topology, labels, support values, and branch-length precision; round-trip check each tree.
2. Compare the six trees and metadata with the original MEGA analyses and published tree figures.
3. For online candidates, verify which FASTA files belong to each PAHG analysis and request/retrieve ML/NJ source trees. A PDF image alone cannot reliably recover the original branch lengths and support values.
4. Continue acquiring source files for the remaining 203 catalogue entries, then repeat the same validation process.
