from io import BytesIO

import pytest
from openpyxl import Workbook

from reviewer.extraction import ExtractorRegistry, UnsupportedDocumentError


def test_extracts_workbook_cells_with_provenance() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "P&L"
    sheet.append(["Revenue", 125000])
    stream = BytesIO()
    workbook.save(stream)

    document = ExtractorRegistry().extract("finance.xlsx", stream.getvalue())

    assert document.parser == "openpyxl"
    assert document.blocks[0].text == "Revenue | 125000"
    assert document.blocks[0].sheet == "P&L"
    assert document.blocks[0].cell_range == "1:1"


def test_rejects_unknown_extension() -> None:
    with pytest.raises(UnsupportedDocumentError):
        ExtractorRegistry().extract("archive.zip", b"data")

