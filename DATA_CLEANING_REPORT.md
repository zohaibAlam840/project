# PAHG data cleaning report — 18 November 2026

## What is now in the project

All 221 family IDs and names were taken from the [official PAHG family
table](https://www.pahgncb.com/genomedb/public/genefamilies). For every ID,
we captured both the official raw sequence FASTA and the official alignment
FASTA: **442 responses, with no failed endpoints**. Each response is preserved
unaltered with its URL, date, byte size and SHA256 in the download manifest.
The older public PAHG GitHub repository supplied 93 additional FASTAs; every
one matches the pinned Git commit's blob hash. These are supplementary
evidence, not replacements for incomplete official downloads.

Working copies were made separately. We inserted **12 missing FASTA header
line breaks** in official downloads and **28** in GitHub files. Three official
responses had a plain-text title before the first FASTA header; only the
working copies omit that title. No protein residue, gap or sequence label was
guessed or replaced. Two GitHub FASTAs are empty and remain flagged. One
GitHub raw FASTA contains an underscore within a protein sequence; that
unknown character remains flagged rather than silently changed.

## Results for the 221 official alignments

| Status | Families | Meaning |
| --- | ---: | --- |
| Source alignment incomplete | **121** | The file ends mid-record, or reaches the 65,535-byte limit with many expected records absent. It cannot be presented as a complete source alignment. |
| Format or pairing review | **32** | All aligned records have equal length, but raw/aligned/published counts, exact protein sequences, or raw FASTA format do not fully agree. |
| Sequence checks pass | **68** | Equal lengths; published, raw, and aligned counts agree; every raw protein matches an ungapped aligned protein exactly; no raw-format issue. Original tree downloads remain unavailable. |

These categories total 221. Three of the 68 passing families (PAHG IDs 1, 2
and 3) also have six separately supplied ML/NJ Newick trees. The other 65 do
not have source tree files in this project.

**Why the incomplete files cannot simply be “fixed”:** 113 official alignment
downloads are exactly 65,535 bytes. For ABLIM (ID 81), PAHG's direct download
is 65,535 bytes and equals the pinned GitHub alignment after CRLF-to-LF line
ending normalization. It has 12 aligned records, the last shortened, whereas
the official raw FASTA has all 66 published records. One other family (ID
179) reaches 65,535 bytes immediately after a complete aligned record but
contains only 16 of 48 expected records. The missing alignment information
is not recoverable by padding with gaps. A fresh alignment could be built
from raw sequences, but it would be a *new analysis*, not PAHG's original.

Of the 221 raw downloads, **176** have the same record count as the official
family table. Fourteen raw FASTAs have a remaining format issue such as
duplicate headers, empty records or unusual sequence characters. We have
recorded specific unmatched headers and record counts for all 32 pairing
review families in `inventory/pairing_review_details.csv`.

## Tree evidence and scientific limits

The six supplied Newick trees parse and have tip labels matching their
associated supplied alignments. Six working NEXUS tree files preserve their
Newick expressions and pass independent parser round trips. Their original
MEGA session analyses have not yet been compared directly with each export.
The COL NJ tree contains a small negative branch length
(`-0.000250018030820602`) that was preserved and flagged for scientific
review. PAHG's public routes expose sequence and alignment downloads, but no
source ML/NJ Newick or NEXUS tree download. PDF tree images are not an
equivalent source for exact branch lengths and support values.

The PAHG family-table sequence counts captured on 15 November 2026 sum to
15,389. The [2025 PAHG publication](https://pmc.ncbi.nlm.nih.gov/articles/PMC12522930/)
reports 15,231. The reason for the difference is not established, so the
inventory keeps the displayed per-family count and tests each file against
its own row rather than forcing the paper total.

## What is still needed to make all 221 research datasets ready

1. Obtain **complete original alignments** for the 121 incomplete families,
   ideally from the PAHG maintainers or the lab's MEGA analysis folders. A
   documented new alignment from raw sequences is a separate option if the
   original cannot be recovered and the supervisor approves the method.
2. Resolve the **32 count or sequence discrepancies** using the exact
   unmatched records in the pairing review log. Several appear to contain
   extra or missing proteins; they cannot be removed by a blanket rule.
3. Obtain source **ML and NJ tree exports or MEGA sessions** for the other
   families, plus model, bootstrap and version metadata. Compare the six
   supplied trees with their MEGA analyses and review the COL NJ branch.
4. Only after those checks should the website label a family as a validated
   phylogenetic analysis. It can already display the inventory and each
   family's current evidence status.

The most useful material the user or supervisor could provide is a shared
folder or archive containing PAHG's original per-family MEGA files, full
alignment exports, and Newick/NEXUS ML/NJ trees. We have completed the
public-source collection and all checks possible without those originals.
