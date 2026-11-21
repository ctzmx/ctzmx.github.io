"""Validate a lab report's source hashes, then regenerate all Markdown tables."""

import hashlib
import json
from pathlib import Path
import statistics
import sys


def main():
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = Path(__file__).resolve().parent
    for name, expected in report["source_sha256"].items():
        actual = hashlib.sha256((root / name).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        if actual != expected:
            raise ValueError(f"Source changed since this report: {name}")
    assert all(check["passed"] for check in report["checks"])
    print(f"Source hashes verified. {len(report['checks'])} checks passed.")
    print(f"Timing: {report['settings']['timing']}; all values in microseconds.\n")
    for group in ("add", "rms", "gemm"):
        print(f"## {group}\n")
        print("| Shape | Implementation | Median µs | Min–max µs | Throughput |")
        print("| --- | --- | ---: | ---: | ---: |")
        rows = [row for row in report["benchmarks"] if row["group"] == group]
        for row in sorted(rows, key=lambda r: (r["shape"], r["implementation"])):
            values = row["samples_us"]
            assert row["median_us"] == statistics.median(values)
            assert row["min_us"] == min(values) and row["max_us"] == max(values)
            throughput = (f"{row['effective_GB_s']:.1f} GB/s" if "effective_GB_s" in row
                          else f"{row['TFLOP_s']:.2f} TFLOP/s" if "TFLOP_s" in row else "—")
            shape = "×".join(map(str, row["shape"]))
            print(f"| {shape} | {row['implementation']} | {row['median_us']:.3f} | "
                  f"{row['min_us']:.3f}–{row['max_us']:.3f} | {throughput} |")
        print()


if __name__ == "__main__":
    main()
