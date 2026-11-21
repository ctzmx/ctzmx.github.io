import torch
import triton
import triton.language as tl


@triton.jit
def add_kernel(X, Y, Z, N: tl.constexpr, BLOCK: tl.constexpr):
    offsets = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    valid = offsets < N
    x = tl.load(X + offsets, mask=valid, other=0)
    y = tl.load(Y + offsets, mask=valid, other=0)
    tl.store(Z + offsets, x + y, mask=valid)


def main():
    x = torch.tensor([1, 2, 3, 4, 5], device="cuda", dtype=torch.float32)
    y = torch.tensor([10, 20, 30, 40, 50], device="cuda", dtype=torch.float32)
    z = torch.empty_like(x)
    block = 128
    grid = (triton.cdiv(x.numel(), block),)
    add_kernel[grid](x, y, z, x.numel(), block, num_warps=4)
    torch.cuda.synchronize()
    torch.testing.assert_close(z, x + y, atol=0, rtol=0)
    print(z.cpu().tolist())


if __name__ == "__main__":
    main()
