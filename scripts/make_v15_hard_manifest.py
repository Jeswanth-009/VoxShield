from __future__ import annotations

import csv
import json
from pathlib import Path


DATA_ROOT = Path("data")
FAILURE_REPORT = Path("artifacts/v14_failure_report.csv")
OUTPUT = DATA_ROOT / "mixtures" / "v15_hard_failures" / "manifest.jsonl"

SOURCES = {
    "v14-onnx-broad-50.json": DATA_ROOT / "mixtures" / "audit_broad_val" / "manifest.jsonl",
    "v14-onnx-military-50.json": DATA_ROOT / "mixtures" / "audit_military_val" / "manifest.jsonl",
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    if not FAILURE_REPORT.exists():
        raise SystemExit(f"missing failure report: {FAILURE_REPORT}")

    manifests = {
        audit: {str(row["id"]): row for row in read_jsonl(path)}
        for audit, path in SOURCES.items()
    }
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()

    with FAILURE_REPORT.open("r", encoding="utf-8-sig", newline="") as handle:
        for failure in csv.DictReader(handle):
            audit = failure["audit"]
            clip_id = str(failure["id"])
            key = (audit, clip_id)
            if key in seen:
                continue
            seen.add(key)
            if audit not in manifests or clip_id not in manifests[audit]:
                raise SystemExit(f"missing source manifest row for {audit} id={clip_id}")
            row = dict(manifests[audit][clip_id])
            row["id"] = f"{audit.removesuffix('.json')}-{clip_id}"
            row["hard_source_suite"] = "broad" if "broad" in audit else "military"
            row["hard_reason"] = {
                "fail_snr": failure["fail_snr"].lower() == "true",
                "fail_stoi": failure["fail_stoi"].lower() == "true",
                "fail_pesq": failure["fail_pesq"].lower() == "true",
            }
            row["v14_metrics"] = {
                "input_snr_db": float(failure["input_snr_db"]),
                "snr_enhanced": float(failure["snr_enhanced"]),
                "stoi_enhanced": float(failure["stoi_enhanced"]),
                "pesq_enhanced": float(failure["pesq_enhanced"]),
            }
            rows.append(row)

    if not rows:
        raise SystemExit("no hard failures selected")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    by_category: dict[str, int] = {}
    by_label: dict[str, int] = {}
    by_suite: dict[str, int] = {}
    for row in rows:
        by_category[str(row.get("category"))] = by_category.get(str(row.get("category")), 0) + 1
        label = str(row.get("noise_source_label") or row.get("source_label") or "unknown")
        by_label[label] = by_label.get(label, 0) + 1
        by_suite[str(row.get("hard_source_suite"))] = by_suite.get(str(row.get("hard_source_suite")), 0) + 1

    print(json.dumps({
        "output": str(OUTPUT),
        "count": len(rows),
        "by_suite": dict(sorted(by_suite.items())),
        "by_category": dict(sorted(by_category.items())),
        "top_labels": dict(sorted(by_label.items(), key=lambda item: item[1], reverse=True)[:12]),
    }, indent=2))


if __name__ == "__main__":
    main()
