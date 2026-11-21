"""Reproducible RTX 5080 teaching lab: checks, CUDA-event timing, raw samples.

Run inside Linux/WSL, with torch 2.9.1+cu128 and triton 3.5.1.
Timing is warm-buffer graph replay by default, not application tokens/s.
"""

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys

import torch
import torch.nn.functional as F
import triton

from kernels import add_into, rms_eager, rms_norm
from matmul import matmul_into


ROOT = Path(__file__).resolve().parent
CHECKS = []


def check(name, actual, expected, atol, rtol):
    torch.testing.assert_close(actual, expected, atol=atol, rtol=rtol)
    difference = (actual.double() - expected.double()).abs()
    CHECKS.append({"name": name, "shape": list(actual.shape), "dtype": str(actual.dtype),
                   "atol": atol, "rtol": rtol,
                   "max_abs_error": difference.max().item() if actual.numel() else 0.0,
                   "passed": True})


def rejects(name, fn):
    try:
        fn()
    except ValueError:
        CHECKS.append({"name": name, "passed": True, "expected": "ValueError"})
    else:
        raise AssertionError(name + " should have rejected the input")


def reference_rms(x, weight):
    # Higher-precision oracle, outside any timed region.
    xd = x.double()
    return (xd * torch.rsqrt(xd.square().mean(-1, keepdim=True) + 1e-6)
            * weight.double()).to(x.dtype)


def correctness():
    for n in (0, 1, 127, 128, 129, 255, 256, 257, 1023, 1024, 1025, 65537):
        x, y = (torch.randn(n, device="cuda") for _ in range(2))
        for block in (128, 256, 1024):
            for warps in (4, 8):
                z = torch.full_like(x, float("nan"))
                check(f"add/n={n}/block={block}/warps={warps}",
                      add_into(x, y, z, block, warps), x + y, 0, 0)
    base = torch.randn(32, device="cuda")
    rejects("add/noncontiguous", lambda: add_into(base[::2], base[::2], torch.empty(16, device="cuda")))
    rejects("add/cpu", lambda: add_into(torch.ones(2), torch.ones(2), torch.empty(2)))
    rejects("add/overlap", lambda: add_into(base[:-1], base[:-1], base[1:]))
    rejects("add/autograd", lambda: add_into(base.clone().requires_grad_(), base, torch.empty_like(base)))
    for dtype in (torch.float16, torch.bfloat16, torch.float32):
        for m, n in ((0, 7), (1, 1), (1, 7), (3, 33), (5, 127), (7, 129), (9, 1025), (4, 4096), (2, 8192)):
            for pattern in ("random", "zero", "large"):
                x = torch.randn((m, n), device="cuda", dtype=dtype)
                if pattern == "zero":
                    x.zero_()
                elif pattern == "large":
                    x.mul_(1000)  # FP16 squaring without upcasting would overflow.
                w = torch.randn(n, device="cuda", dtype=dtype)
                atol, rtol = ((2e-6, 2e-5) if dtype == torch.float32 else
                              (2e-3, 2e-3) if dtype == torch.float16 else (2e-2, 2e-2))
                for warps in (4, 8):
                    check(f"rms/{m}x{n}/{pattern}/warps={warps}",
                          rms_norm(x, w, num_warps=warps), reference_rms(x, w), atol, rtol)
    rejects("rms/noncontiguous", lambda: rms_norm(torch.randn(8, 8, device="cuda").T, torch.ones(8, device="cuda")))
    rejects("rms/width-zero", lambda: rms_norm(torch.empty((1, 0), device="cuda"), torch.empty(0, device="cuda")))
    rejects("rms/width-too-large", lambda: rms_norm(torch.zeros((1, 8193), device="cuda"), torch.ones(8193, device="cuda")))
    rejects("rms/nan-eps", lambda: rms_norm(base.reshape(1, 32), base, eps=float("nan")))
    rejects("rms/autograd", lambda: rms_norm(base.reshape(1, 32).requires_grad_(), base))
    for m, n, k in ((1, 1, 1), (31, 65, 33), (65, 67, 129), (128, 128, 128)):
        a = torch.randn((m, k), device="cuda", dtype=torch.float16)
        b = torch.randn((k, n), device="cuda", dtype=torch.float16)
        ref = (a.double() @ b.double()).half()
        for bm, bn, bk, warps in ((32, 64, 32, 4), (64, 64, 32, 4), (64, 128, 32, 8)):
            c = torch.full((m, n), float("nan"), device="cuda", dtype=torch.float16)
            check(f"gemm/{m}x{n}x{k}/{bm}x{bn}x{bk}/warps={warps}",
                  matmul_into(a, b, c, bm, bn, bk, warps), ref, 2e-2, 1e-2)
    a = torch.randn((32, 32), device="cuda", dtype=torch.float16)
    b, c = torch.randn_like(a), torch.empty_like(a)
    rejects("gemm/noncontiguous", lambda: matmul_into(a.T, b, c))
    rejects("gemm/shape", lambda: matmul_into(a, b, c[:16]))
    rejects("gemm/overlap", lambda: matmul_into(a, b, a))
    rejects("gemm/autograd", lambda: matmul_into(a.requires_grad_(), b, c))
    torch.cuda.synchronize()


def measure(fn, samples=9, inner=64, timing="graph"):
    # Compilation, allocation initialization, and clocks warming happen first.
    warm_stream = torch.cuda.Stream()
    warm_stream.wait_stream(torch.cuda.current_stream())
    with torch.cuda.stream(warm_stream):
        for _ in range(30):
            fn()
    torch.cuda.current_stream().wait_stream(warm_stream)
    torch.cuda.synchronize()
    graph = None
    if timing == "graph":
        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph, stream=warm_stream):
            for _ in range(inner):
                fn()
        for _ in range(5):
            graph.replay()
        torch.cuda.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    values = []
    for _ in range(samples):
        start.record()
        if graph is None:
            for _ in range(inner):
                fn()
        else:
            graph.replay()
        end.record()
        end.synchronize()
        values.append(start.elapsed_time(end) * 1000 / inner)
    return {"median_us": statistics.median(values), "min_us": min(values),
            "max_us": max(values), "samples_us": values,
            "inner": inner, "sample_count": samples, "timing": timing}


def benchmarks(args):
    rows = []
    def run(group, shape, impl, fn, nbytes=None, flops=None):
        result = {"group": group, "shape": list(shape), "implementation": impl,
                  **measure(fn, args.samples, args.inner, args.timing)}
        if nbytes is not None:
            result["logical_bytes"] = nbytes
            result["effective_GB_s"] = nbytes / (result["median_us"] * 1000)
        if flops is not None:
            result["conventional_flops"] = flops
            result["TFLOP_s"] = flops / (result["median_us"] * 1e6)
        print(f"{group:6} {str(shape):24} {impl:28} {result['median_us']:9.3f} us", flush=True)
        rows.append(result)

    for n in (1024, 1048576, 16777216):
        x, y = (torch.randn(n, device="cuda") for _ in range(2))
        z = torch.empty_like(x)
        ref = x + y
        candidates = [("torch.add(out)", lambda: torch.add(x, y, out=z))]
        for block, warps in ((128, 4), (256, 4), (1024, 4), (1024, 8)):
            fn = lambda block=block, warps=warps: add_into(x, y, z, block, warps)
            check(f"bench/add/{n}/{block}/{warps}", fn(), ref, 0, 0)
            candidates.append((f"triton/B{block}/W{warps}", fn))
        random.shuffle(candidates)
        for name, fn in candidates:
            run("add", (n,), name, fn, nbytes=12 * n)

    for m, n in ((1, 4096), (32, 4096), (1024, 4096), (257, 1537)):
        x = torch.randn((m, n), device="cuda", dtype=torch.float16)
        w = torch.randn(n, device="cuda", dtype=torch.float16)
        ref = reference_rms(x, w)
        candidates = [("torch eager fp32", lambda: rms_eager(x, w)),
                      ("torch F.rms_norm", lambda: F.rms_norm(x, (n,), w, eps=1e-6)),
                      ("triton/W4", lambda: rms_norm(x, w, num_warps=4)),
                      ("triton/W8", lambda: rms_norm(x, w, num_warps=8))]
        random.shuffle(candidates)
        for name, fn in candidates:
            # Native implementation may use different intermediate rounding.
            check(f"bench/rms/{m}x{n}/{name}", fn(), ref, 1e-2, 1e-2)
            run("rms", (m, n), name, fn)

    for m, n, k in ((1, 1024, 1024), (128, 512, 512), (1024, 1024, 1024), (257, 513, 255)):
        a = torch.randn((m, k), device="cuda", dtype=torch.float16)
        b = torch.randn((k, n), device="cuda", dtype=torch.float16)
        c = torch.empty((m, n), device="cuda", dtype=torch.float16)
        # CPU float64 reference is independent of the GPU GEMM implementation.
        ref = (a.cpu().double() @ b.cpu().double()).to(device="cuda", dtype=torch.float16)
        candidates = [("torch.mm(out)", lambda: torch.mm(a, b, out=c))]
        for bm, bn, bk, warps in ((32, 64, 32, 4), (64, 64, 32, 4), (64, 128, 32, 8)):
            fn = lambda bm=bm, bn=bn, bk=bk, warps=warps: matmul_into(a, b, c, bm, bn, bk, warps)
            candidates.append((f"triton/{bm}x{bn}x{bk}/W{warps}", fn))
        random.shuffle(candidates)
        for name, fn in candidates:
            check(f"bench/gemm/{m}x{n}x{k}/{name}", fn(), ref, 5e-2, 1e-2)
            run("gemm", (m, n, k), name, fn, flops=2 * m * n * k)
    return rows


def gpu_snapshot():
    try:
        cmd = ["/usr/lib/wsl/lib/nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,power.draw,clocks.sm,clocks.mem", "--format=csv"]
        return subprocess.check_output(cmd, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("check", "bench", "all"), default="all")
    parser.add_argument("--timing", choices=("graph", "events"), default="graph")
    parser.add_argument("--samples", type=int, default=9)
    parser.add_argument("--inner", type=int, default=64)
    parser.add_argument("--output", type=Path, default=Path("results.json"))
    args = parser.parse_args()
    if args.samples < 3 or args.inner < 1:
        parser.error("need samples >= 3 and inner >= 1")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU not available")
    torch.manual_seed(20261121)
    random.seed(20261121)
    torch.set_num_threads(8)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = False
    torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction = False
    device = torch.cuda.get_device_properties(0)
    payload = {
        "timestamp": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        "environment": {"platform": platform.system(), "kernel": platform.release(),
                        "linux_distribution": platform.freedesktop_os_release().get("PRETTY_NAME", "unknown"),
                        "gcc": subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0],
                        "python": sys.version.split()[0], "torch": torch.__version__,
                        "torch_cuda_runtime": torch.version.cuda, "triton": triton.__version__,
                        "gpu": device.name, "compute_capability": [device.major, device.minor],
                        "total_memory_bytes": device.total_memory,
                        "multiprocessor_count": device.multi_processor_count},
        "source_sha256_normalization": "UTF-8, LF line endings",
        "source_sha256": {p.name: hashlib.sha256(p.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
                          for p in sorted(ROOT.glob("*.py"))},
        "settings": {"seed": 20261121, "timing": args.timing, "samples": args.samples,
                     "inner": args.inner, "warmup_calls": 30, "graph_warmup_replays": 5,
                     "mode": args.mode, "tf32": False, "fp16_reduced_precision_reduction": False,
                     "input_cache": "same buffers reused, no cache flush",
                     "candidate_order": "fixed-seed shuffle within each shape",
                     "scope": "forward only; no compilation, H2D/D2H or CPU allocation in graph timing"},
        "gpu_before": gpu_snapshot(),
    }
    with torch.inference_mode():
        if args.mode in ("check", "all"):
            correctness()
            print(f"Correctness: {len(CHECKS)} checks passed", flush=True)
        # Keep benchmark tensors identical across --mode all / bench and timing modes.
        torch.manual_seed(20261121)
        random.seed(20261121)
        payload["benchmarks"] = benchmarks(args) if args.mode in ("bench", "all") else []
    payload["checks"] = CHECKS
    payload["gpu_after"] = gpu_snapshot()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {args.output}; {len(CHECKS)} checks passed", flush=True)


if __name__ == "__main__":
    main()
