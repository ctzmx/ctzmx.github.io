"""Forward-only teaching kernels. CUDA contiguous tensors; no autograd contract."""

import math

import torch
import triton
import triton.language as tl


def _overlaps(x, y):
    return (x.numel() > 0 and y.numel() > 0
            and x.data_ptr() < y.data_ptr() + y.numel() * y.element_size()
            and y.data_ptr() < x.data_ptr() + x.numel() * x.element_size())


@triton.jit
def add_kernel(X, Y, Z, N: tl.constexpr, BLOCK: tl.constexpr):
    offsets = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    valid = offsets < N
    x = tl.load(X + offsets, mask=valid, other=0)
    y = tl.load(Y + offsets, mask=valid, other=0)
    tl.store(Z + offsets, x + y, mask=valid)


def add_into(x, y, z, block=256, num_warps=4):
    """Write a contiguous FP32 vector sum; each tensor has at most 2**31 - 1 elements."""
    if not (x.is_cuda and y.is_cuda and z.is_cuda):
        raise ValueError("CUDA tensors required")
    if not (x.device == y.device == z.device):
        raise ValueError("same device required")
    if not all(t.is_contiguous() and t.ndim == 1 for t in (x, y, z)):
        raise ValueError("contiguous 1-D tensors required")
    if not (x.shape == y.shape == z.shape and x.dtype == y.dtype == z.dtype == torch.float32):
        raise ValueError("equal shapes and float32 required")
    if x.numel() > 2**31 - 1:
        raise ValueError("teaching kernel 32-bit index limit: at most 2**31 - 1 elements per tensor")
    if any(t.requires_grad for t in (x, y, z)) or _overlaps(x, z) or _overlaps(y, z):
        raise ValueError("forward only; output must not overlap inputs")
    if block <= 0 or block & (block - 1) or num_warps not in (4, 8):
        raise ValueError("power-of-two block and num_warps in (4, 8) required")
    # Empty input has no work and must not launch a zero-sized grid.
    if x.numel():
        with torch.cuda.device(x.device):
            add_kernel[(triton.cdiv(x.numel(), block),)](
                x, y, z, x.numel(), block, num_warps=num_warps
            )
    return z


@triton.jit
def rms_kernel(X, W, Y, N: tl.constexpr, EPS: tl.constexpr, BLOCK: tl.constexpr):
    row = tl.program_id(0)
    cols = tl.arange(0, BLOCK)
    x = tl.load(X + row * N + cols, mask=cols < N, other=0).to(tl.float32)
    w = tl.load(W + cols, mask=cols < N, other=0).to(tl.float32)
    mean_square = tl.sum(x * x, axis=0) / N
    y = x * tl.rsqrt(mean_square + EPS) * w
    tl.store(Y + row * N + cols, y, mask=cols < N)


def rms_norm(x, weight, eps=1e-6, num_warps=4):
    """Normalize contiguous rows; x has at most 2**31 - 1 elements and width <= 8192."""
    if not (x.is_cuda and weight.is_cuda and x.device == weight.device):
        raise ValueError("CUDA tensors on same device required")
    if x.ndim != 2 or weight.ndim != 1 or weight.numel() != x.shape[1]:
        raise ValueError("expected X[M,N], weight[N]")
    if not (x.is_contiguous() and weight.is_contiguous()):
        raise ValueError("contiguous tensors required")
    if x.dtype != weight.dtype or x.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        raise ValueError("matching fp16, bf16 or fp32 required")
    if x.requires_grad or weight.requires_grad:
        raise ValueError("forward only; autograd not implemented")
    if not (0 < x.shape[1] <= 8192) or not math.isfinite(eps) or eps <= 0 or num_warps not in (4, 8):
        raise ValueError("1 <= N <= 8192, positive eps, num_warps in (4,8) required")
    if x.numel() > 2**31 - 1:
        raise ValueError("teaching kernel 32-bit index limit: at most 2**31 - 1 elements per tensor")
    y = torch.empty_like(x)
    if x.shape[0]:
        with torch.cuda.device(x.device):
            rms_kernel[(x.shape[0],)](
                x, weight, y, x.shape[1], eps,
                triton.next_power_of_2(x.shape[1]), num_warps=num_warps,
            )
    return y


def rms_eager(x, weight, eps=1e-6):
    """Same formula, FP32 intermediates and output dtype; reduction order can differ."""
    xf = x.float()
    return (xf * torch.rsqrt((xf * xf).mean(dim=-1, keepdim=True) + eps)
            * weight.float()).to(x.dtype)
