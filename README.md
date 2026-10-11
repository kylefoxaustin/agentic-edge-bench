# agentic-edge-bench

**What does an agentic AI workload actually *cost* on edge silicon — and what resource sets the ceiling?**

A small, honest benchmark that answers one question with measurements instead of datasheet math:

> ### Decode is bound by **memory bandwidth**, not by **TOPS**.
> The token-generation loop of an on-device agent is fed by DRAM bandwidth and CPU. A big NPU earns
> its area on *perception* (vision, ASR) and on *prefill/TTFT* — **not** on the agent's generation
> loop. So you should size the **subsystem** (bandwidth, memory capacity, accelerator placement) to
> the model tier your product needs — not chase a TOPS number.

You can reproduce the headline on your own laptop in **two commands**, no GPU required, and run the
same decode ladder across edge boards over SSH.

![python](https://img.shields.io/badge/python-3.9%2B-blue) ![cpu](https://img.shields.io/badge/works-CPU--only-brightgreen) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

---

## 30-second quick start (any x86 laptop, pure CPU)

```bash
git clone https://github.com/kylefoxaustin/agentic-edge-bench
cd agentic-edge-bench
pip install llama-cpp-python          # the only dependency for the demo
python3 scripts/x86_demo.py            # downloads a 2 GB model, benches your CPU
```

It self-downloads a small model, checks it fits in RAM, benches prefill + decode, and prints the
punchline — **what fraction of your DDR bandwidth the generation loop sustains, with the GPU/NPU
completely idle.** Example (a real run on an Intel i9-14900KF, dual-channel DDR5-5600):

```
  prefill   : 228.4 tok/s  [MEASURED]  (compute-bound; scales with threads)
  decode    :  32.95 tok/s [MEASURED]  (bandwidth-bound; ~flat vs threads)
  eff. mem BW:  65.9 GB/s   [DERIVED: decode × weights]
  DDR util  :  73.5 %       → decode runs at 73.5% of peak DDR, zero GPU/NPU
```

Add `--tasks` to also run three real agentic tasks (email draft, file-summarize, grounded Q&A)
against the model — each one turns out to be 70–90% decode, i.e. bandwidth-bound too. Full detail:
[`docs/RUN_X86_DEMO.md`](docs/RUN_X86_DEMO.md).

---

## The cross-board decode ladder

The same instrument, run across edge accelerators, gives a comparable decode/prefill ladder.
Measured on our hardware (your numbers will differ — report your own board + model + date):

| board | class | model | decode tok/s | prefill tok/s | provenance |
|---|---|---:|---:|---:|---|
| RTX 5090 | desktop dGPU (Blackwell) | 7B | 217.9 | — | MEASURED (reference) |
| **localhost-x86** | **CPU only (i9-14900KF)** | **3B** | **32.95** | **228.4** | **MEASURED (this repo)** |
| Jetson AGX Thor | edge GPU (sm_110) | 7B | 20.9 | 799 | MEASURED |
| Jetson AGX Orin | edge GPU (sm_87) | 7B | 14.5 | 527 | MEASURED |
| i.MX95 + Kinara Ara-2 | edge NPU accelerator | 3B | 13.1 | — | MEASURED (live) |
| Qualcomm IQ-9075 | Hexagon (Genie) | 7B | 9.5 | 596 | SOURCED (vendor) |
| i.MX95 (A55 CPU only) | edge CPU | 7B | 1.9 | 3.2 | MEASURED |

Two things fall out that you can't get from a spec sheet:
- **Decode tracks memory bandwidth, not TOPS.** The ordering is a bandwidth ordering. The CPU-only
  i.MX95 rung (1.9 tok/s) shows what happens with no bandwidth help; the accelerator rung (13.1)
  shows the lift — and *that lift is bandwidth, not compute*.
- **Prefill and decode are different workloads.** Prefill is compute-bound (it scales with cores and
  SIMD — see the x86 demo's thread sweep); decode is bandwidth-bound (nearly flat vs threads). An
  accelerator helps the first and barely touches the second. That's the whole sizing argument.

Run it on your own board (Jetson, i.MX, any SSH-reachable Linux box with llama.cpp):
[`docs/RUN_BOARDS.md`](docs/RUN_BOARDS.md). Full measured context: [`docs/RESULTS.md`](docs/RESULTS.md).

---

## What's measured, and how it's labelled

Every number in this repo carries one of three provenance tags, and they never get mixed in a
comparison:

| tag | meaning |
|---|---|
| **MEASURED** | we ran it, on this hardware — the only kind that appears bare or in a headline |
| **DERIVED** | computed from measurements (e.g. effective bandwidth = decode × weight bytes) — always labelled |
| **SOURCED** | from a vendor datasheet or the literature — labelled, used only where we couldn't measure |

A derived or sourced number is never compared head-to-head against a measured one. This is the
single discipline that keeps an edge-silicon comparison honest.

---

## Accuracy is a separate axis (optional)

Resource cost and answer quality are different questions. An optional two-judge grader scores task
outputs PASS/PARTIAL/FAIL using **two models from different families** (Claude + GPT-4o), both at
temperature 0, flagging disagreements rather than averaging them:

```bash
python3 scripts/x86_demo.py --tasks            # produce task outputs
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... # (grader only; the benchmark needs no keys)
python3 eval/judge_agentic_tasks.py
```

A finding this surfaces immediately: a small model's accuracy is bounded by **grounding**, not
size — the grounded Q&A (facts in the prompt) passes while the ungrounded summary fabricates.

---

## Repo layout

```
scripts/
  x86_demo.py          # the pure-CPU laptop demo (start here)
  bench_board.py       # per-board decode/prefill driver (SSH)
  provision.py         # feasibility gate + model staging ("can this board run this model?")
  aggregate_boards.py  # combine per-board runs into the ladder
eval/
  model_registry.json  # models (HF repo, size, arch) + board definitions
  test_catalog.json    # the task catalog
  judge_agentic_tasks.py  # optional two-judge accuracy grader
  results/             # measured results (the ladder + per-board runs)
docs/
  RUN_X86_DEMO.md      # the laptop demo, in depth
  RUN_BOARDS.md        # running the ladder on your own boards
  RESULTS.md           # measured ladder + methodology
```

## Requirements

- Python 3.9+
- `llama-cpp-python` (CPU is fine) for the x86 demo
- For boards: a `llama.cpp` build on each board (CUDA for Jetsons, CPU otherwise) reachable over SSH
- For grading (optional): `anthropic` + `openai` and the respective API keys

```bash
pip install -r requirements.txt
```

## License

MIT — see [`LICENSE`](LICENSE).
