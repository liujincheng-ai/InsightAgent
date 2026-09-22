import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_DIR = REPO_ROOT / "insight_agent" / "evaluation" / "dataset"
KNOWLEDGE_DIR = REPO_ROOT / "insight_agent" / "knowledge"

EXPECTED_KNOWLEDGE_FILES = {
    "2026年度经营目标.md",
    "经销商分级与考核管理制度.md",
    "重点客户流失预警办法.md",
    "汽车配件价格与折扣管理办法.md",
    "库存与补货管理规范.md",
    "产品质量与售后处理规范.md",
}


def load_json(filename: str) -> dict:
    return json.loads((EVALUATION_DIR / filename).read_text(encoding="utf-8"))


def test_day2_text_to_sql_cases_are_fixed() -> None:
    dataset = load_json("day2_text_to_sql.json")

    assert dataset["baseline_model"] == "deepseek-v4-flash"
    assert dataset["evaluation_policy"]["fresh_conversation_per_case"] is True
    assert dataset["evaluation_policy"]["score_first_generated_sql_only"] is True
    assert len(dataset["cases"]) == 10
    assert [case["id"] for case in dataset["cases"]] == [
        f"sql-{number:02d}" for number in range(1, 11)
    ]


def test_day2_rag_cases_and_parameters_are_fixed() -> None:
    dataset = load_json("day2_rag.json")

    assert dataset["baseline_model"] == "deepseek-v4-flash"
    assert dataset["embedding"] == "BAAI/bge-small-zh-v1.5"
    assert dataset["vector_store"] == "ChromaDB"
    assert dataset["retrieval"] == {
        "chunk_size": 512,
        "chunk_overlap": 50,
        "top_k": 5,
    }
    assert len(dataset["cases"]) == 4


def test_six_synthetic_knowledge_documents_have_numbered_sections() -> None:
    actual_files = {path.name for path in KNOWLEDGE_DIR.glob("*.md")}
    assert actual_files == EXPECTED_KNOWLEDGE_FILES

    for path in KNOWLEDGE_DIR.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        assert "合成制度" in content
        assert "## 1." in content
        assert "### " in content


def test_rag_gold_sources_exist_in_documents() -> None:
    dataset = load_json("day2_rag.json")

    for case in dataset["cases"][:3]:
        content = (KNOWLEDGE_DIR / case["gold_document"]).read_text(encoding="utf-8")
        assert case["gold_section"] in content

    for source in dataset["cases"][3]["gold_sources"]:
        content = (KNOWLEDGE_DIR / source["document"]).read_text(encoding="utf-8")
        assert source["section"] in content
