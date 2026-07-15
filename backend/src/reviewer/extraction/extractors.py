from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Protocol

from openpyxl import load_workbook

from reviewer.extraction.models import ExtractedBlock, ExtractedDocument


class UnsupportedDocumentError(ValueError):
    pass


class Extractor(Protocol):
    extensions: frozenset[str]

    def extract(self, filename: str, content: bytes) -> ExtractedDocument: ...


def _block(
    text: str,
    source: str,
    offset: int,
    **location: int | str | None,
) -> ExtractedBlock:
    page = location.get("page")
    sheet = location.get("sheet")
    cell_range = location.get("cell_range")
    return ExtractedBlock(
        text=text,
        source=source,
        start_offset=offset,
        end_offset=offset + len(text),
        page=page if isinstance(page, int) else None,
        sheet=sheet if isinstance(sheet, str) else None,
        cell_range=cell_range if isinstance(cell_range, str) else None,
        kind=str(location.get("kind") or "text"),
    )


class PlainTextExtractor:
    extensions = frozenset({".txt", ".md", ".json"})

    def extract(self, filename: str, content: bytes) -> ExtractedDocument:
        text = content.decode("utf-8-sig")
        return ExtractedDocument(
            filename=filename,
            parser="plain-text",
            blocks=[_block(text, filename, 0)],
        )


class CsvExtractor:
    extensions = frozenset({".csv"})

    def extract(self, filename: str, content: bytes) -> ExtractedDocument:
        rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
        blocks: list[ExtractedBlock] = []
        offset = 0
        for row_number, row in enumerate(rows, start=1):
            text = " | ".join(value.strip() for value in row)
            blocks.append(
                _block(
                    text,
                    filename,
                    offset,
                    kind="table-row",
                    cell_range=f"{row_number}:{row_number}",
                )
            )
            offset += len(text) + 1
        return ExtractedDocument(filename=filename, parser="python-csv", blocks=blocks)


class PdfExtractor:
    extensions = frozenset({".pdf"})

    def extract(self, filename: str, content: bytes) -> ExtractedDocument:
        import fitz  # type: ignore[import-untyped]

        blocks: list[ExtractedBlock] = []
        warnings: list[str] = []
        offset = 0
        with fitz.open(stream=content, filetype="pdf") as document:
            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text").strip()
                if not text:
                    warnings.append(f"Page {page_number} has no embedded text; OCR is required.")
                    continue
                blocks.append(_block(text, filename, offset, page=page_number))
                offset += len(text) + 1
        return ExtractedDocument(
            filename=filename,
            parser="pymupdf",
            blocks=blocks,
            warnings=warnings,
        )


class DocxExtractor:
    extensions = frozenset({".docx"})

    def extract(self, filename: str, content: bytes) -> ExtractedDocument:
        from docx import Document as WordDocument

        document = WordDocument(io.BytesIO(content))
        blocks: list[ExtractedBlock] = []
        offset = 0
        for paragraph_number, paragraph in enumerate(document.paragraphs, start=1):
            text = paragraph.text.strip()
            if text:
                blocks.append(_block(text, filename, offset, cell_range=f"P{paragraph_number}"))
                offset += len(text) + 1
        for table_number, table in enumerate(document.tables, start=1):
            for row_number, row in enumerate(table.rows, start=1):
                text = " | ".join(cell.text.strip() for cell in row.cells)
                blocks.append(
                    _block(
                        text,
                        filename,
                        offset,
                        kind="table-row",
                        cell_range=f"T{table_number}:R{row_number}",
                    )
                )
                offset += len(text) + 1
        return ExtractedDocument(filename=filename, parser="python-docx", blocks=blocks)


class XlsxExtractor:
    extensions = frozenset({".xlsx"})

    def extract(self, filename: str, content: bytes) -> ExtractedDocument:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        blocks: list[ExtractedBlock] = []
        offset = 0
        for sheet in workbook.worksheets:
            for row_number, values in enumerate(sheet.iter_rows(values_only=True), start=1):
                rendered = ["" if value is None else str(value) for value in values]
                if not any(rendered):
                    continue
                text = " | ".join(rendered)
                blocks.append(
                    _block(
                        text,
                        filename,
                        offset,
                        kind="table-row",
                        sheet=sheet.title,
                        cell_range=f"{row_number}:{row_number}",
                    )
                )
                offset += len(text) + 1
        return ExtractedDocument(filename=filename, parser="openpyxl", blocks=blocks)


class ExtractorRegistry:
    def __init__(self, extractors: list[Extractor] | None = None) -> None:
        self._extractors = extractors or [
            PlainTextExtractor(),
            CsvExtractor(),
            PdfExtractor(),
            DocxExtractor(),
            XlsxExtractor(),
        ]

    @property
    def supported_extensions(self) -> set[str]:
        return {extension for extractor in self._extractors for extension in extractor.extensions}

    def extract(self, filename: str, content: bytes) -> ExtractedDocument:
        extension = Path(filename).suffix.lower()
        for extractor in self._extractors:
            if extension in extractor.extensions:
                return extractor.extract(filename, content)
        supported = ", ".join(sorted(self.supported_extensions))
        raise UnsupportedDocumentError(
            f"Unsupported file type {extension!r}; expected {supported}."
        )
