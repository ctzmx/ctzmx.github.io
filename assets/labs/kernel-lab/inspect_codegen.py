"""Inspect one compiled teaching GEMM on this installed Triton version."""

import argparse
import hashlib
import json
from pathlib import Path

import torch
import triton

from matmul import _matmul_kernel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("codegen.json"))
    args = parser.parse_args()
    torch.manual_seed(20261121)
    a = torch.randn((128, 128), device="cuda", dtype=torch.float16)
    b = torch.randn_like(a)
    c = torch.empty_like(a)
    compiled = _matmul_kernel[(4, 2)](a, b, c, 128, 128, 128, 32, 64, 32,
                                    num_warps=4, num_stages=3)
    torch.cuda.synchronize()
    torch.testing.assert_close(c, (a.double() @ b.double()).half(), atol=2e-2, rtol=1e-2)
    ptx = compiled.asm["ptx"]
    instructions = sorted({line.strip().split(" ")[0].split("\t")[0]
                           for line in ptx.splitlines()
                           if "mma.sync" in line or "tcgen05.mma" in line or "wgmma.mma" in line})
    result = {"torch": torch.__version__, "triton": triton.__version__,
              "gpu": torch.cuda.get_device_name(),
              "compute_capability": list(torch.cuda.get_device_capability()),
              "kernel": "_matmul_kernel", "shape_MNK": [128, 128, 128],
              "tile": [32, 64, 32], "num_warps": 4, "num_stages": 3,
              "registers_per_thread": compiled.n_regs,
              "shared_memory_bytes": compiled.metadata.shared,
              "matrix_instructions_in_ptx": instructions,
              "ptx_sha256": hashlib.sha256(ptx.encode()).hexdigest(),
              "source_sha256_normalization": "UTF-8, LF line endings",
              "source_sha256": {p.name: hashlib.sha256(p.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
                                for p in (Path(__file__), Path(__file__).with_name("matmul.py"))},
              "correctness_passed": True,
              "note": "PTX inspection is version-specific; this is not SASS or a profiler measurement."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
