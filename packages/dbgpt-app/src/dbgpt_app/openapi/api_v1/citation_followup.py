"""Deterministic citation-summary support for multi-turn knowledge chat."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Optional, Sequence

from .react_final import AgentCitation, AgentFinalAnswer

_FOLLOWUP_MARKERS = ("来源", "制度", "章节", "引用", "出处")
_SECTION_PATTERN = re.compile(
    r"(?:^|[-#：:\"'\s|])"
    r"([1-9]\d*(?:\.\d+)+\s*[^\r\n\"|]{0,100})",
    flags=re.MULTILINE,
)


@dataclass(frozen=True)
class _PriorCitation:
    citation: AgentCitation
    section: str


def is_citation_followup(question: str) -> bool:
    """Return whether a question asks to summarize earlier answer sources."""

    normalized = re.sub(r"\s+", "", question or "")
    refers_back = any(
        marker in normalized for marker in ("以上", "上述", "前面", "分别")
    )
    asks_source = any(marker in normalized for marker in _FOLLOWUP_MARKERS)
    return refers_back and asks_source


def _payload_from_message(message: Any) -> Optional[dict[str, Any]]:
    if getattr(message, "type", None) != "view":
        return None
    content = getattr(message, "content", None)
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        return None
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _basename(value: str) -> str:
    windows_name = PureWindowsPath(value).name
    return PurePosixPath(windows_name).name


def _document_name_from_text(*values: Any) -> Optional[str]:
    """Recover a document name when a retriever emits a generic source label."""

    for value in values:
        if not isinstance(value, str):
            continue
        md_match = re.search(r"([^\s\"《》:/\\]+\.md)", value)
        if md_match:
            return _basename(md_match.group(1))
        candidates = re.findall(r"《([^》]+)》", value)
        heading_match = re.search(r"[\"']([^\r\n\"']+?)-\d+(?:\.|\s)", value)
        if heading_match:
            candidates.append(heading_match.group(1))
        for candidate in candidates:
            normalized = re.sub(
                r"^.*?(?:股份有限公司|有限责任公司|有限公司)\s*",
                "",
                candidate.strip(),
            )
            if normalized and re.search(r"(?:制度|办法|规范|指南|标准)$", normalized):
                return normalized + ".md"
    return None


def _section_candidates(value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    sections: list[str] = []
    for match in _SECTION_PATTERN.finditer(value):
        section = match.group(1).strip(" #：:-")
        if section and section not in sections:
            sections.append(section)
    return sections


def _section_number(section: str) -> str:
    match = re.match(r"^(\d+(?:\.\d+)+)", section)
    return match.group(1) if match else ""


def _section_relevance(section: str, final_text: str) -> int:
    title = re.sub(r"^\d+(?:\.\d+)+\s*", "", section)
    normalized_title = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", title)
    bigrams = {
        normalized_title[index : index + 2]
        for index in range(max(0, len(normalized_title) - 1))
    }
    score = sum(1 for token in bigrams if token in final_text)
    if _section_number(section) and _section_number(section) in final_text:
        score += 20
    return score


def _section_from_text(final_content: Any, *excerpts: Any) -> str:
    """Choose the section most strongly supported by the answer and excerpts."""

    final_text = final_content if isinstance(final_content, str) else ""
    final_sections = _section_candidates(final_content)
    excerpt_sections = [
        section for excerpt in excerpts for section in _section_candidates(excerpt)
    ]
    for final_section in final_sections:
        final_number = _section_number(final_section)
        same_number = [
            section
            for section in excerpt_sections
            if _section_number(section) == final_number
        ]
        if same_number:
            return max(
                same_number,
                key=lambda section: (
                    _section_relevance(section, final_text),
                    len(section),
                ),
            )
    if final_sections:
        return max(
            final_sections,
            key=lambda section: _section_relevance(section, final_text),
        )

    if excerpt_sections:
        # Retrieval excerpts can contain adjacent headings.  Prefer the heading
        # whose title bigrams occur most often in the final answer, then the
        # later heading (grep context commonly places the matched section last).
        def relevance(item: tuple[int, str]) -> tuple[int, int]:
            position, section = item
            return _section_relevance(section, final_text), position

        return max(enumerate(excerpt_sections), key=relevance)[1]

    return "章节见引用片段"


def _citation_from_dict(
    item: dict[str, Any], index: int, final_content: str
) -> Optional[AgentCitation]:
    source = item.get("sourceName") or item.get("source_name") or item.get("path")
    excerpt = item.get("excerpt")
    if not isinstance(excerpt, str) or not excerpt.strip():
        return None
    generic_source = not isinstance(source, str) or source.strip().casefold() in {
        "knowledge base",
        "knowledge_base",
        "知识库",
        "unknown",
    }
    if generic_source:
        source = _document_name_from_text(final_content, excerpt)
    if not isinstance(source, str) or not source.strip():
        return None
    return AgentCitation(
        index=index,
        id=str(item.get("id") or f"history-citation-{index}"),
        source_name=_basename(source.strip()),
        excerpt=excerpt.strip(),
        score=item.get("score")
        if isinstance(item.get("score"), (int, float))
        else None,
        path=item.get("path") if isinstance(item.get("path"), str) else None,
        url=item.get("url") if isinstance(item.get("url"), str) else None,
        primary_section=(
            item.get("primarySection")
            if isinstance(item.get("primarySection"), str)
            else item.get("primary_section")
            if isinstance(item.get("primary_section"), str)
            else None
        ),
    )


def _best_round_citation(
    payload: dict[str, Any], index: int
) -> Optional[_PriorCitation]:
    citations = payload.get("citations")
    if not isinstance(citations, list):
        return None
    final_content = payload.get("final_content") or ""
    final_sections = _section_candidates(final_content)
    primary_section_number = (
        _section_number(final_sections[0]) if final_sections else ""
    )
    candidates: list[tuple[int, AgentCitation, str]] = []
    for raw in citations:
        if not isinstance(raw, dict):
            continue
        citation = _citation_from_dict(raw, index, str(final_content))
        if citation is None:
            continue
        section = citation.primary_section or _section_from_text(
            final_content, citation.excerpt
        )
        score = 0
        if citation.source_name in str(final_content):
            score += 4
        if section != "章节见引用片段":
            score += 2
            score += _section_relevance(section, str(final_content))
        if (
            primary_section_number
            and _section_number(section) == primary_section_number
        ):
            score += 100
        if citation.source_name.lower().endswith(".md"):
            score += 1
        candidates.append((score, citation, section))
    if not candidates:
        return None
    _, citation, section = max(candidates, key=lambda item: item[0])
    return _PriorCitation(citation=citation, section=section)


def build_citation_followup_answer(
    messages: Sequence[Any] | Iterable[Any], minimum_sources: int = 3
) -> Optional[AgentFinalAnswer]:
    """Build a source summary from citations already saved in earlier rounds."""

    rounds: list[_PriorCitation] = []
    seen_sources: set[str] = set()
    for message in messages:
        payload = _payload_from_message(message)
        if payload is None:
            continue
        prior = _best_round_citation(payload, len(rounds) + 1)
        if prior is None:
            continue
        source_key = prior.citation.source_name.casefold()
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)
        rounds.append(prior)

    if len(rounds) < minimum_sources:
        return None
    selected = rounds[-minimum_sources:]
    citations = tuple(
        AgentCitation(
            index=index,
            id=prior.citation.id,
            source_name=prior.citation.source_name,
            excerpt=prior.citation.excerpt,
            score=prior.citation.score,
            path=prior.citation.path,
            url=prior.citation.url,
            primary_section=prior.citation.primary_section,
        )
        for index, prior in enumerate(selected, start=1)
    )
    lines = [
        f"{index}. 《{prior.citation.source_name}》— {prior.section}"
        for index, prior in enumerate(selected, start=1)
    ]
    content = "以上三个答案的制度与章节来源分别是：\n\n" + "\n".join(lines)
    return AgentFinalAnswer(content=content, citations=citations)
