from pydantic import BaseModel, Field


class ExtractedBlock(BaseModel):
    text: str
    source: str
    kind: str = "text"
    page: int | None = None
    sheet: str | None = None
    cell_range: str | None = None
    start_offset: int = 0
    end_offset: int = 0
    attributes: dict[str, str | float | int | bool | None] = Field(default_factory=dict)


class ExtractedDocument(BaseModel):
    filename: str
    parser: str
    blocks: list[ExtractedBlock]
    warnings: list[str] = Field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(block.text for block in self.blocks)

