# Measured results

Numbers are hardware-specific. Report your own board + model + date; these are ours.
Provenance tags per the repo rule: **MEASURED** (ran it) / **DERIVED** (computed) / **SOURCED**
(vendor / literature). A derived or sourced number is never compared bare against a measured one.

## The decode / prefill ladder (7B-class Q4, except where marked 3B)

| board | runtime | model | decode tok/s | prefill tok/s | tag |
|---|---|---:|---:|---:|---|
| RTX 5090 | CUDA (Blackwell dGPU) | 7B | 217.9 | — | MEASURED (reference, n=3) |
| Jetson AGX Thor | CUDA (sm_110) | 7B | 40.68 | 1,601 | MEASURED |
| Jetson AGX Thor | CUDA (sm_110) | 14B | 20.86 | 799 | MEASURED |
| Jetson AGX Orin | CUDA (sm_87) | 7B | 27.76 | 1,074 | MEASURED |
| Jetson AGX Orin | CUDA (sm_87) | 14B | 14.54 | 527 | MEASURED |
| Qualcomm IQ-9075 | Hexagon / Genie | 7B | 9.45 | 596 | MEASURED 2026-09-15, Genie runtime (separate toolchain, not llama-bench) |
| i.MX95 (A55 CPU only) | llama.cpp CPU | 7B | 1.9 | 3.2 | MEASURED |
| i.MX95 + Kinara Ara-2 | Kinara `.dvm` | 7B | 6.3 | — | MEASURED 2026-07 (dated; within 3% of NXP's published 6.51) |
| i.MX95 + Kinara Ara-2 | Kinara `.dvm` | 3B | 13.1 | — | MEASURED (live; 3B) |
| localhost-x86 (i9-14900KF) | llama.cpp CPU | 3B | 32.53 | 226.3 | MEASURED (this repo) |

**Keep model size in view.** Decode cost is ~linear in model size, so the 3B rungs (Kinara, x86)
are not directly comparable to the 7B rungs. Compare within a size, or scale by the parameter ratio
(and label it DERIVED).

## What the ladder shows

1. **Decode tracks memory bandwidth, not TOPS.** The ordering is a bandwidth ordering. On the same
   i.MX95 and the same 7B model, the CPU-only path decodes at 1.92 tok/s and the Kinara accelerator
   at 6.3 (3.3×): the lift comes from feeding the loop faster, not from raw compute.
   **Size penalty:** 7B → 14B costs 1.95× on Thor and 1.91× on Orin, matching the 1.94× parameter
   ratio — time per token scales with the bytes streamed, whatever the architecture.

2. **Prefill ≠ decode.** Prefill is compute-bound; decode is bandwidth-bound. The x86 demo makes
   this visible directly: on an i9-14900KF, prefill went **40 → 215 tok/s** moving from 24 to 16
   threads (the 16 slow E-cores were dragging the compute-bound phase), while decode barely moved
   (31–34 tok/s) — because decode is waiting on DRAM, not cores. An accelerator helps prefill/TTFT
   and barely touches the decode loop.

3. **Effective bandwidth, derived.** A dense model reads ~all its weights from DRAM once per
   generated token, so `effective_read_BW ≈ decode_tok/s × weight_bytes` [DERIVED]. On the x86 box
   that's 32.53 tok/s × 2.0 GB ≈ **65.1 GB/s**, i.e. **~72.7%** of the box's ~89.6 GB/s peak
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
- The Qualcomm rung uses a different runtime (Genie) and is dated; the Kinara 7B rung is dated and the 3B rung is a live run. All are labelled.
- This measures *resource cost*, not answer quality — see the optional two-judge grader for the
  accuracy axis.

## Corrections

- **2026-10-28:** the Thor and Orin "7B" rows (20.9 and 14.5 tok/s) were 14B runs. A run with
  `--provision qwen2.5-14b` overwrote each board's 7B result file and the aggregator labelled it 7B.
  The 7B rows are now 40.68 (Thor) and 27.76 (Orin); the 14B runs are kept as their own rows.
  `bench_board.py` now writes provisioned models to `<board>@<model>.json`, and
  `aggregate_boards.py` reads the provisioned model's size.
