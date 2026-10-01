from __future__ import annotations

import json
from pathlib import Path


DATA_ROOT = Path("data")
OUTPUT = DATA_ROOT / "mixtures" / "v12_hard_failures" / "manifest.jsonl"

SOURCES = [
    (
        "broad",
        Path("artifacts/v10-final-broad-50.json"),
        DATA_ROOT / "mixtures" / "audit_broad_val" / "manifest.jsonl",
    ),
    (
        "military",
        Path("artifacts/v10-final-military-50.json"),
        DATA_ROOT / "mixtures" / "audit_military_val" / "manifest.jsonl",
    ),
]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def is_hard(record: dict) -> bool:
    category = str(record.get("category", ""))
    return (
        category == "mixed"
        or float(record.get("snr_enhanced") or 0.0) < 18.0
        or float(record.get("si_snr_enhanced") or 0.0) < 18.0
        or float(record.get("stoi_enhanced") or 0.0) < 0.88
        or float(record.get("pesq_enhanced") or 0.0) < 3.0
    )


def main() -> None:
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for suite, report_path, manifest_path in SOURCES:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        manifest_by_id = {str(row["id"]): row for row in read_jsonl(manifest_path)}
        for record in report["records"]:
            if not is_hard(record):
                continue
            key = (suite, str(record["id"]))
            if key in seen:
                continue
            seen.add(key)
            row = dict(manifest_by_id[str(record["id"])])
            row["id"] = f"{suite}-{row['id']}"
            row["hard_source_suite"] = suite
            row["hard_reason"] = {
                "mixed": str(record.get("category")) == "mixed",
                "snr_enhanced_lt_18": float(record.get("snr_enhanced") or 0.0) < 18.0,
                "si_snr_enhanced_lt_18": float(record.get("si_snr_enhanced") or 0.0) < 18.0,
                "stoi_enhanced_lt_0_88": float(record.get("stoi_enhanced") or 0.0) < 0.88,
                "pesq_enhanced_lt_3_0": float(record.get("pesq_enhanced") or 0.0) < 3.0,
            }
            row["v10_metrics"] = {
                name: record.get(name)
                for name in (
                    "snr_enhanced",
                    "si_snr_enhanced",
                    "stoi_enhanced",
                    "pesq_enhanced",
                    "snr_improvement",
                    "si_snr_improvement",
                    "stoi_improvement",
                    "pesq_improvement",
                )
            }
            rows.append(row)
    if not rows:
        raise SystemExit("no hard examples selected")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    by_category: dict[str, int] = {}
    by_suite: dict[str, int] = {}
    for row in rows:
        by_category[str(row.get("category"))] = by_category.get(str(row.get("category")), 0) + 1
        by_suite[str(row.get("hard_source_suite"))] = by_suite.get(str(row.get("hard_source_suite")), 0) + 1
    print(json.dumps({
        "output": str(OUTPUT),
        "count": len(rows),
        "by_suite": by_suite,
        "by_category": by_category,
    }, indent=2))


if __name__ == "__main__":
    main()
