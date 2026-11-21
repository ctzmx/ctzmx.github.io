"""A small forward-only FP16 GEMM for learning tiled GPU computation.

Each Triton program owns a BLOCK_M x BLOCK_N output tile.  The K loop
loads an A tile and a B tile, reuses them in ``tl.dot``, and accumulates
in FP32.  This is a teaching implementation, not a replacement for
cuBLAS or a production GEMM library.  It accepts contiguous 2-D tensors
only and does not implement autograd, bias, batching, or split-K.
"""

import torch
import triton
import triton.language as tl


@triton.jit
def _matmul_kernel(
    A, B, C,
    M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    # A program is a cooperating group of GPU threads, not one thread.
    rows = tl.program_id(0) * BLOCK_M + tl.arange(0, BLOCK_M)
    cols = tl.program_id(1) * BLOCK_N + tl.arange(0, BLOCK_N)
    inner = tl.arange(0, BLOCK_K)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for tile in range(tl.cdiv(K, BLOCK_K)):
        ks = tile * BLOCK_K + inner
        a = tl.load(
            A + rows[:, None] * K + ks[None, :],
            mask=(rows[:, None] < M) & (ks[None, :] < K),
            other=0.0,
        )
        b = tl.load(
            B + ks[:, None] * N + cols[None, :],
            mask=(ks[:, None] < K) & (cols[None, :] < N),
            other=0.0,
        )
        acc = tl.dot(a, b, acc)

    tl.store(
        C + rows[:, None] * N + cols[None, :],
        acc.to(tl.float16),
        mask=(rows[:, None] < M) & (cols[None, :] < N),
    )


def _overlaps(x, y):
    """Exact address-span overlap for the contiguous tensors accepted here."""
    x_start, y_start = x.data_ptr(), y.data_ptr()
    x_end = x_start + x.numel() * x.element_size()
    y_end = y_start + y.numel() * y.element_size()
    return x_start < y_end and y_start < x_end


def matmul_into(
    a, b, c, block_m=32, block_n=64, block_k=32, num_warps=4,
):
    """Write ``a @ b`` to preallocated ``c`` and return ``c``.

    All tensors must be nonempty, contiguous, two-dimensional CUDA
    FP16 tensors on the same device; ``a`` is [M, K], ``b`` is [K, N],
    and ``c`` is [M, N].  Output may not overlap either input.  Inputs
    requiring gradients are rejected because this example is forward-only.
    Each matrix may contain at most 2**31 - 1 elements because the teaching
    kernel uses 32-bit indices.
    The column grid requires ceil(N / block_n) <= 65535 on CUDA.
    Kernel execution is asynchronous with respect to the CPU.
    """
    tensors = (a, b, c)
    if not all(isinstance(t, torch.Tensor) for t in tensors):
        raise TypeError("a, b, c must be torch.Tensor objects")
    if not all(t.is_cuda and t.dtype == torch.float16 for t in tensors):
        raise ValueError("a, b, c must be CUDA float16 tensors")
    if not all(t.device == a.device for t in tensors):
        raise ValueError("a, b, c must be on the same CUDA device")
    if not all(t.ndim == 2 and t.is_contiguous() for t in tensors):
        raise ValueError("a, b, c must be contiguous 2-D tensors")
    if not all(t.numel() > 0 for t in tensors):
        raise ValueError("this example requires nonempty matrices")
    if any(t.numel() > 2**31 - 1 for t in tensors):
        raise ValueError("teaching kernel 32-bit index limit: at most 2**31 - 1 elements per tensor")
    if any(t.requires_grad for t in tensors):
        raise ValueError("this teaching kernel does not implement autograd")
    m, k = a.shape
    k_b, n = b.shape
    if k != k_b or c.shape != (m, n):
        raise ValueError("expected a[M,K], b[K,N], c[M,N]")
    if _overlaps(c, a) or _overlaps(c, b):
        raise ValueError("output c must not overlap a or b")
    if block_m not in (16, 32, 64, 128) or block_n not in (16, 32, 64, 128):
        raise ValueError("block_m and block_n must be 16, 32, 64, or 128")
    if block_k not in (16, 32, 64):
        raise ValueError("block_k must be 16, 32, or 64")
    if num_warps not in (4, 8):
        raise ValueError("this example supports num_warps=4 or 8")
    if triton.cdiv(n, block_n) > 65535:
        raise ValueError("teaching kernel CUDA grid.y limit: ceil(N / block_n) must be <= 65535")
    with torch.cuda.device(a.device):
        _matmul_kernel[(triton.cdiv(m, block_m), triton.cdiv(n, block_n))](
            a, b, c, m, n, k, block_m, block_n, block_k,
            num_warps=num_warps, num_stages=3,
        )
    return c
