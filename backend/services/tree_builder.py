"""Build a lightweight, page-aware hierarchy from extracted legal PDF text."""

import re
from dataclasses import dataclass, field
from typing import Any, Optional


CHAPTER_PATTERN = re.compile(
    r"^\s*(?:chapter|chap\.)\s+(?:[ivxlcdm]+|\d+)\b.*$", re.IGNORECASE
)
SECTION_PATTERN = re.compile(
    r"^\s*(?:section|sec\.)\s+(?:\d+(?:\.\d+)*|[ivxlcdm]+)\b.*$",
    re.IGNORECASE,
)
NUMBERED_HEADING_PATTERN = re.compile(
    r"^\s*\d+(?:\.\d+)*[.)]\s+.{1,100}$"
)


@dataclass
class DocumentNode:
    id: str
    title: str
    type: str
    text: str = ""
    page: Optional[int] = None
    children: list["DocumentNode"] = field(default_factory=list)
    _last_text_page: Optional[int] = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "text": self.text,
            "page": self.page,
            "children": [child.to_dict() for child in self.children],
        }


def build_document_tree(pages: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a JSON-serializable document tree from page-level extracted text."""
    node_count = 0

    def create_node(title: str, node_type: str, page: Optional[int]) -> DocumentNode:
        nonlocal node_count
        node_count += 1
        return DocumentNode(
            id=f"node-{node_count}", title=title, type=node_type, page=page
        )

    def append_text(node: DocumentNode, text: str, page: int) -> None:
        text = text.strip()
        if not text:
            return
        if node.text:
            separator = "\n\n" if node._last_text_page != page else "\n"
            if node._last_text_page != page:
                separator += f"[Page {page}]\n"
            node.text += separator
        node.text += text
        node.page = node.page or page
        node._last_text_page = page

    root = create_node("Document", "document", None)
    current_chapter = root
    current_section: Optional[DocumentNode] = None
    current_content = root

    for page_data in pages:
        page_number = int(page_data["page"])
        page_text = str(page_data.get("text", ""))

        for line in page_text.splitlines():
            heading = line.strip()
            if not heading:
                continue

            if CHAPTER_PATTERN.match(heading):
                current_chapter = create_node(heading, "chapter", page_number)
                root.children.append(current_chapter)
                current_section = None
                current_content = current_chapter
            elif SECTION_PATTERN.match(heading):
                current_section = create_node(heading, "section", page_number)
                current_chapter.children.append(current_section)
                current_content = current_section
            elif NUMBERED_HEADING_PATTERN.match(heading):
                parent = current_section or current_chapter
                current_content = create_node(heading, "heading", page_number)
                parent.children.append(current_content)
            else:
                append_text(current_content, line, page_number)

    return root.to_dict()
