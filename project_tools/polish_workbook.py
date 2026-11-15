"""Add Excel navigation features after artifact-tool layout/export."""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent
if ROOT.name == "project_tools":
    ROOT = ROOT.parent
FILE = ROOT / "inventory" / "PAHG_master_inventory.xlsx"
wb = load_workbook(FILE)
for ws in wb:
    ws.freeze_panes = "D6" if ws.title == "Master inventory" else "C6" if ws.title in {"Tree files", "Online data"} else "B6"
    ws.auto_filter.ref = f"A5:{get_column_letter(ws.max_column)}{ws.max_row}"
    ws.sheet_view.zoomScale = 85 if ws.title == "Master inventory" else 90
    ws.print_title_rows = "1:5"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.tabColor = "137C87" if ws.title == "Master inventory" else "637D90"
    headers = {ws.cell(5, c).value: c for c in range(1, ws.max_column + 1)}
    for title in ("PAHG family page", "Raw URL", "Alignment URL"):
        if title not in headers:
            continue
        col = headers[title]
        for row in range(6, ws.max_row + 1):
            cell = ws.cell(row, col)
            if isinstance(cell.value, str) and cell.value.startswith("https://"):
                cell.hyperlink = cell.value
                cell.font = Font(name="Aptos", size=10, color="137C87", underline="single")
wb.save(FILE)
print(FILE)
