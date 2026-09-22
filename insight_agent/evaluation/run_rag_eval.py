"""Run the frozen Week 3 retrieval, answer and citation benchmark."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .citation_check import score_structured_answer
from .rag_metrics import (
    score_retrieval_case,
    summarize_answer_records,
    summarize_retrieval_records,
)
from .rag_retrieval import (
    build_chunks,
    embedding_model,
    index_fingerprint,
    prepare_store,
    search_store,
)
from .rag_schemas import (
    load_rag_dataset,
    select_rag_cases,
    validate_rag_dataset,
)
from .schemas import file_sha256


def run(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset)
    dataset = load_rag_dataset(dataset_path)
    errors = validate_rag_dataset(dataset)
    if errors:
        raise ValueError("Week 3 数据集校验失败:\n- " + "\n- ".join(errors))
    cases = select_rag_cases(dataset, args.split)
    if args.case_id:
        requested = set(args.case_id)
        cases = [case for case in cases if case["id"] in requested]
        missing = requested - {case["id"] for case in cases}
        if missing:
            raise ValueError("未找到指定评测 ID: " + ", ".join(sorted(missing)))
    output_dir = Path(args.output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"结果目录非空，拒绝覆盖: {output_dir}")
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    corpus_paths = [Path(args.knowledge_dir), Path(args.distractor_dir)]
    corpus_hash = _corpus_hash(corpus_paths)
    chunks = build_chunks(
        corpus_paths, chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap
    )
    embedding = None
    if args.retriever == "vector":
        embedding = embedding_model(args.embedding_model, args.embedding_cache)
    index_name = index_fingerprint(
        retriever=args.retriever,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        corpus_hash=corpus_hash,
        run_id=output_dir.name,
    )
    store = prepare_store(
        retriever=args.retriever,
        chunks=chunks,
        index_name=index_name,
        vector_path=Path(args.vector_path),
        embedding=embedding,
        elasticsearch_url=args.elasticsearch_url,
        elasticsearch_port=args.elasticsearch_port,
    )
    records: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']} {case['question']}", flush=True)
        started = time.perf_counter()
        results = search_store(
            retriever=args.retriever,
            store=store,
            query=case["question"],
            top_k=args.top_k,
            query_strategy=args.query_strategy,
        )
        retrieval_latency = round(time.perf_counter() - started, 4)
        record = {
            "id": case["id"],
            "split": case["split"],
            "case_type": case["case_type"],
            "question": case["question"],
            "should_answer": case["should_answer"],
            "gold_sources": case["gold_sources"],
            "retrieved": results,
            "retrieval_latency_seconds": retrieval_latency,
            **score_retrieval_case(case, results, top_k=args.top_k),
        }
        if args.mode == "answer":
            prompt = _answer_prompt(case, results)
            generation_started = time.perf_counter()
            raw_answer = _chat_completion(
                args.endpoint,
                model=args.model,
                prompt=prompt,
                timeout=args.timeout,
            )
            record.update(
                {
                    "model": args.model,
                    "temperature": 0.0,
                    "raw_answer": raw_answer,
                    "generation_latency_seconds": round(
                        time.perf_counter() - generation_started, 3
                    ),
                    **score_structured_answer(case, raw_answer, retrieved=results),
                }
            )
        records.append(record)
        (raw_dir / f"{case['id']}.json").write_text(
            json.dumps({"case": case, "record": record}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    retrieval_summary = summarize_retrieval_records(records, top_k=args.top_k)
    summary: dict[str, Any] = {"retrieval": retrieval_summary}
    if args.mode == "answer":
        summary["answer"] = summarize_answer_records(records)
    (output_dir / "records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest = {
        "run_id": output_dir.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "retriever": args.retriever,
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "top_k": args.top_k,
        "query_strategy": args.query_strategy,
        "model": args.model if args.mode == "answer" else None,
        "temperature": 0.0 if args.mode == "answer" else None,
        "split": args.split,
        "case_count": len(cases),
        "chunk_count": len(chunks),
        "dataset_sha256": file_sha256(dataset_path),
        "corpus_sha256": corpus_hash,
        "index_name": index_name,
        "git_commit": _git_value("rev-parse", "HEAD"),
        "git_branch": _git_value("branch", "--show-current"),
        "git_dirty": bool(_git_value("status", "--porcelain")),
        "raw_trace_preserved": True,
        "summary": summary,
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _answer_prompt(case: dict[str, Any], results: list[dict[str, Any]]) -> str:
    context = "\n\n".join(
        f"[证据 {item['rank']}] 文档={item['document']} 章节={item['section']} "
        f"状态={item['status']} chunk={item['chunk_id']}\n{item['content']}"
        for item in results
    )
    return f"""你是 InsightAgent 的制度问答模块。只能使用给定证据回答问题。

规则：
1. 只有状态为 active 的正式制度可以支持当前制度结论；
   obsolete 或 distractor 只能用于识别冲突，不能作为当前依据。
2. 每个制度性事实必须在 claims 中绑定真实文档名、章节和原文证据。
   问题含多个并列子问题时必须逐项回答，不能只回答第一个主题。
   优先保留原文中的阈值、职责、例外、时限和证据要求。
3. 如果证据没有明确回答问题，answer 必须说明“证据不足”，
   insufficient_evidence=true，claims=[]。
4. 不得使用常识补齐制度，不得虚构文档、条款、数字或责任人。
5. 仅返回一个 JSON 对象，不要 Markdown 代码块。

JSON 格式：
{{
  "answer": "面向用户的中文回答",
  "insufficient_evidence": false,
  "claims": [
    {{
      "claim": "一项可以独立核验的结论",
      "source_document": "包含扩展名的文档名",
      "section": "章节号，例如 4.2",
      "evidence": "支持该结论的原文短句"
    }}
  ]
}}

问题：{case["question"]}

检索证据：
{context}
"""


def _chat_completion(endpoint: str, *, model: str, prompt: str, timeout: float) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "stream": False,
        "max_tokens": 3000,
        "chat_mode": "chat_normal",
        "conv_uid": f"week3-{uuid.uuid4()}",
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return str(body["choices"][0]["message"]["content"])


def _corpus_hash(paths: list[Path]) -> str:
    import hashlib

    digest = hashlib.sha256()
    for root in paths:
        for path in sorted(root.glob("*.md")):
            digest.update(path.name.encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, encoding="utf-8", stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("retrieval", "answer"), default="retrieval")
    parser.add_argument("--retriever", choices=("vector", "bm25"), required=True)
    parser.add_argument(
        "--chunk-size", type=int, choices=(256, 512, 800), required=True
    )
    parser.add_argument(
        "--chunk-overlap", type=int, choices=(0, 50, 100), required=True
    )
    parser.add_argument("--top-k", type=int, choices=(3, 5, 8), required=True)
    parser.add_argument(
        "--query-strategy", choices=("single", "decompose"), default="single"
    )
    parser.add_argument(
        "--split", choices=("dev", "test", "challenge", "all"), default="dev"
    )
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--endpoint", default="http://127.0.0.1:5670/api/v2/chat/completions"
    )
    parser.add_argument(
        "--dataset",
        default=str(root / "insight_agent/evaluation/dataset/rag_test.json"),
    )
    parser.add_argument(
        "--knowledge-dir", default=str(root / "insight_agent/knowledge")
    )
    parser.add_argument(
        "--distractor-dir",
        default=str(root / "insight_agent/evaluation/fixtures/rag_distractors"),
    )
    parser.add_argument("--vector-path", default=str(root / "pilot/data/week3_eval"))
    parser.add_argument("--embedding-model", default="BAAI/bge-small-zh-v1.5")
    parser.add_argument("--embedding-cache")
    parser.add_argument("--elasticsearch-url", default="127.0.0.1")
    parser.add_argument("--elasticsearch-port", default="9200")
    parser.add_argument("--output-dir", required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
