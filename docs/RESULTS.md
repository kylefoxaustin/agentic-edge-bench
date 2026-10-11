# Measured results

Numbers are hardware-specific. Report your own board + model + date; these are ours.
Provenance tags per the repo rule: **MEASURED** (ran it) / **DERIVED** (computed) / **SOURCED**
(vendor / literature). A derived or sourced number is never compared bare against a measured one.

## The decode / prefill ladder (7B-class Q4, except where marked 3B)

| board | runtime | model | decode tok/s | prefill tok/s | tag |
|---|---|---:|---:|---:|---|
| RTX 5090 | CUDA (Blackwell dGPU) | 7B | 217.9 | — | MEASURED (reference, n=3) |
| Jetson AGX Thor | CUDA (sm_110) | 7B | 20.9 | 799 | MEASURED |
| Jetson AGX Orin | CUDA (sm_87) | 7B | 14.5 | 527 | MEASURED |
| Qualcomm IQ-9075 | Hexagon / Genie | 7B | 9.5 | 596 | SOURCED (vendor, dated) |
| i.MX95 (A55 CPU only) | llama.cpp CPU | 7B | 1.9 | 3.2 | MEASURED |
| i.MX95 + Kinara Ara-2 | Kinara `.dvm` | 3B | 13.1 | — | MEASURED (live; 3B) |
| localhost-x86 (i9-14900KF) | llama.cpp CPU | 3B | 32.95 | 228.4 | MEASURED (this repo) |

**Keep model size in view.** Decode cost is ~linear in model size, so the 3B rungs (Kinara, x86)
are not directly comparable to the 7B rungs. Compare within a size, or scale by the parameter ratio
(and label it DERIVED).

## What the ladder shows

1. **Decode tracks memory bandwidth, not TOPS.** The ordering is a bandwidth ordering. The CPU-only
   i.MX95 (1.9 tok/s, no bandwidth help) vs the same SoC with the Kinara accelerator (13.1 tok/s on
   3B) shows the lift comes from feeding the loop faster — not from raw compute.

2. **Prefill ≠ decode.** Prefill is compute-bound; decode is bandwidth-bound. The x86 demo makes
   this visible directly: on an i9-14900KF, prefill went **40 → 215 tok/s** moving from 24 to 16
   threads (the 16 slow E-cores were dragging the compute-bound phase), while decode barely moved
   (31–34 tok/s) — because decode is waiting on DRAM, not cores. An accelerator helps prefill/TTFT
   and barely touches the decode loop.

3. **Effective bandwidth, derived.** A dense model reads ~all its weights from DRAM once per
   generated token, so `effective_read_BW ≈ decode_tok/s × weight_bytes` [DERIVED]. On the x86 box
   that's 32.95 tok/s × 2.0 GB ≈ **65.9 GB/s**, i.e. **~73.5%** of the box's ~89.6 GB/s peak
   DDR5-5600 [SOURCED]. Decode runs near the memory ceiling with the GPU/NPU idle.

## Per-task decode share (x86 `--tasks`, 3B)

Even real agentic tasks are decode-dominated. Prefill/decode time split estimated from the measured
rates [DERIVED]:

| task | gen tokens | decode share | note |
|---|---:|---:|---|
| Email drafting | 256 | ~92% | pure generation |
| File read + summarize | 160 | ~83% | file-tool + decode |
| Grounded spec Q&A (inline) | ~60 | ~73% | shortest answer, still decode-bound |

Every task lands on bandwidth, not TOPS — which is the point of sizing the subsystem to the model.

## The sizing takeaway

For an on-device agent's generation loop, **TOPS do not set the rate — memory bandwidth and CPU
do.** Size the subsystem to the model tier the product needs:
- a decode path that actually *feeds* the engine (bandwidth), not just a big TOPS number,
- enough DRAM for weights + KV at your context length,
- an accelerator aimed at **perception and prefill/TTFT**, where it earns its area.

## Honesty notes

- Numbers are a snapshot of specific hardware/software; re-measure on yours.
- The Qualcomm rung is vendor-sourced and dated; the Kinara rung is a 3B live run. Both are labelled.
- This measures *resource cost*, not answer quality — see the optional two-judge grader for the
  accuracy axis.
