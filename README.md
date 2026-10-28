# agentic-edge-bench

**What does it actually cost to run an AI agent on an edge chip, and which part of the chip sets the limit?**

Spec sheets answer with TOPS. We measured it instead, from a desktop GPU down to a Cortex-A55, and the answer is different:

> ### An agent's speed is set by **memory bandwidth**, not by **TOPS**.
> The loop that generates an agent's words reads the whole model from DRAM for every token. A bigger NPU barely moves it; a faster memory path does. The NPU earns its silicon on **perception** (vision, speech) and on **prefill** (reading the prompt), not on the agent's generation loop. So size the memory subsystem for the model your product needs, and stop chasing a TOPS number.

You can reproduce that on your own laptop in **two commands**, with no GPU, on Linux or Windows. Then run the identical measurement on Jetson, NXP i.MX and Qualcomm boards and get a ladder you can compare.

![python](https://img.shields.io/badge/python-3.9%2B-blue) ![cpu](https://img.shields.io/badge/works-CPU--only-brightgreen) [![x86 demo (Windows + Linux)](https://github.com/kylefoxaustin/agentic-edge-bench/actions/workflows/x86-demo.yml/badge.svg)](https://github.com/kylefoxaustin/agentic-edge-bench/actions/workflows/x86-demo.yml) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Why this benchmark is different

- **It measures cost, not just success.** Mainstream agent benchmarks (AgentBench, τ-bench, WebArena) score whether a task succeeded, not what it cost the silicon; only a few recent efforts have started on resources. This one splits every task into prefill, decode and the overhead around the model, and shows which hardware resource each part leans on.
- **One instrument, laptop to edge board.** The same llama.cpp measurement runs on an x86 laptop, an RTX 5090, Jetson Thor and Orin, and an NXP i.MX95 with and without an accelerator. The Qualcomm IQ-9075 was measured with its own Genie runtime. Board numbers sit side by side.
- **It tells you before it fails.** A feasibility gate checks whether a model fits a board's memory and runtime and refuses with a reason (`UNRUNNABLE — won't fit: ~12 GB > 8 GB`) instead of crashing halfway through a download.
- **Every number says where it came from.** Each figure is tagged MEASURED, DERIVED or SOURCED, and a derived or sourced number is never ranked against a measured one.
- **Accuracy is graded separately, by two judges.** A fast wrong answer isn't a result. An optional grader has Claude and GPT-4o score each task output independently; disagreements are flagged, never averaged.
- **The laptop demo is tested on every change.** CI runs it on fresh Windows and Linux machines (badge above), using the exact commands below.

---

## Run it yourself in two minutes

**Linux / WSL2**
```bash
git clone https://github.com/kylefoxaustin/agentic-edge-bench
cd agentic-edge-bench
pip install --prefer-binary llama-cpp-python huggingface-hub --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
python3 scripts/x86_demo.py --tasks
```

**Windows (PowerShell)**, with Python 3.9+ from python.org or `winget install Python.Python.3.12`:
```powershell
git clone https://github.com/kylefoxaustin/agentic-edge-bench
cd agentic-edge-bench
py -m pip install --prefer-binary llama-cpp-python huggingface-hub --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
py scripts\x86_demo.py --tasks
```

That's it: no compiler, no GPU, no Docker, no server. The demo downloads a 2 GB model (Qwen2.5-3B), checks it fits in your RAM, measures prefill and decode on your CPU, and runs three small agentic tasks. A real run on an Intel i9-14900KF with dual-channel DDR5-5600:

```
  prefill   : 226.3 tok/s  [MEASURED]  (compute-bound; scales with threads)
  decode    :  32.53 tok/s [MEASURED]  (bandwidth-bound; ~flat vs threads)
  eff. mem BW:  65.1 GB/s   [DERIVED: decode × weights]
  DDR util  :  72.7 %       → decode runs at 72.7% of peak DDR, zero GPU/NPU
```

Your CPU is generating text at nearly three-quarters of its memory's rated speed, with the GPU doing nothing. That's the whole thesis, on your own desk. Options, thread counts (`--threads N`), bigger models (`--model 7b`) and troubleshooting: [`docs/RUN_X86_DEMO.md`](docs/RUN_X86_DEMO.md).

---

## What it tests

| Layer | What it measures | How |
|---|---|---|
| **Prefill vs decode** | Tokens/s for reading the prompt (compute-bound) and generating the answer (bandwidth-bound), measured separately | `x86_demo.py` on a laptop; `bench_board.py` (llama-bench) on boards |
| **Thread scaling** | Prefill scales with cores and SIMD; decode stays almost flat, because it's waiting on DRAM | `x86_demo.py --threads N`, run at a few values |
| **Bandwidth utilization** | Effective memory bandwidth = decode tok/s × model size, as a % of the memory's rated peak (DERIVED) | `x86_demo.py`, `bench_board.py` |
| **Agentic tasks on a laptop** | Email drafting, file read → summarize, grounded spec Q&A: how much of a real task is decode | `x86_demo.py --tasks` |
| **Will it fit?** | Weights + KV cache vs board memory, and runtime/architecture support, checked before anything downloads | `provision.py <board> <model> --check-only` |
| **Board ladder** | The same decode/prefill measurement on each board, with the board reserved and checked for competing jobs first | `bench_board.py <board>` → `aggregate_boards.py` |
| **Model-size penalty** | 7B vs 14B on the same board | `bench_board.py <board> --provision qwen2.5-14b` |
| **Accuracy** (optional) | Two judges from different model families grade each task output correct / partial / fabricated | `eval/judge_agentic_tasks.py` |

The full **10-task agentic suite** goes further: RAG over a 31,939-chunk datasheet corpus, web search, Whisper transcription, OCR, a sandboxed script, a multi-tool chain and a long-context brief, each timed per phase. It needs a running agent server and vector database, so it lives in the parent project: [personal-ai-framework / RUN_BENCHMARKS.md](https://github.com/kylefoxaustin/personal-ai-framework/blob/main/docs/RUN_BENCHMARKS.md). The task definitions are in [`eval/test_catalog.json`](eval/test_catalog.json).

---

## What we found

### 1. The decode ladder: same model, same measurement, six machines

Qwen 2.5, Q4_K_M. Your numbers will differ: report your own board, model and date.

| Board | Class | Model | Decode tok/s | Prefill tok/s | Tag |
|---|---|---:|---:|---:|---|
| RTX 5090 | desktop GPU (Blackwell) | 7B | 217.9 | — | MEASURED (full agent stack, n=3) |
| Jetson AGX Thor | edge GPU (sm_110) | 7B | 40.68 | 1,601 | MEASURED |
| Jetson AGX Orin | edge GPU (sm_87) | 7B | 27.76 | 1,074 | MEASURED |
| Qualcomm IQ-9075 | Hexagon NPU (Genie) | 7B | 9.45 | 596 | MEASURED 2026-09-15 with Qualcomm's Genie runtime, not this repo's llama-bench |
| NXP i.MX95 + Kinara ARA240 | M.2 accelerator | 7B | 6.3 | — | MEASURED 2026-07 (within 3% of NXP's published 6.51) |
| NXP i.MX95, A55 CPU only | edge CPU | 7B | 1.92 | 3.2 | MEASURED |
| x86 laptop/desktop (i9-14900KF) | CPU only | 3B | 32.53 | 226 | MEASURED (`x86_demo.py`) |

### 2. Speed follows bandwidth, and it shows in three ways

- **The ladder is a bandwidth ladder.** Thor reaches ~190 GB/s of its 273 GB/s (70%) and Orin ~130 of 204.8 GB/s (63%) (DERIVED: decode × 4.68 GB of weights, against vendor peaks). The i.MX95's A55 cores reach only ~9 GB/s, which is why they decode at 1.92 tok/s.
- **Double the model, half the speed, on every board.** 7B → 14B: Thor 40.68 → 20.86 (1.95×), Orin 27.76 → 14.54 (1.91×), RTX 5090 1.93×. The parameter ratio is 1.94×. The architecture doesn't matter; the bytes per token do.
- **An accelerator helps by feeding the loop.** On the same i.MX95 and the same 7B model, the ARA240 lifts decode from 1.92 to 6.3 tok/s (3.3×). The on-chip Neutron NPU speeds up prefill 8.4× at 512 tokens but leaves decode flat (1.08×) (MEASURED).

### 3. Agents pay a tax outside the model

From the full 10-task suite. On an RTX 5090, every document-grounded task spends a **fixed 0.8–1.0 s** outside the model, on retrieval, prompt building and the agent loop (MEASURED; it repeats to ~1% between runs). That's 15–38% of each task. On Thor's ARM cores the same layer projects to ~5 s, about 39% of a RAG task (DERIVED from a measured 6.6× retrieval slowdown). The first, cold call takes **89 s vs ~2 s warm** (MEASURED, n=1), almost all of it loading the retrieval stack. And on the smallest parts the retrieved context is itself the tax: a 4,400-token RAG prompt exceeds the IQ-9075 NPU's ~256-token prompt cap and falls back to the CPU.

### 4. Small models still invent details

Two judges graded a stock 7B on the 10 tasks and agreed on 4 clean passes (file ops, transcription, OCR, script running). Open-ended writing fabricated hardware specs even when fluent. On the laptop demo, grounded Q&A (facts in the prompt) passes while an ungrounded summary fabricates. Report cost per **successful** task, not cost per task.

Full tables and method: [`docs/RESULTS.md`](docs/RESULTS.md).

---

## Run it on your own boards

Any SSH-reachable Linux board with a llama.cpp build (CUDA for Jetsons, CPU otherwise):

```bash
python3 scripts/provision.py orin qwen2.5-14b --check-only   # will it fit? RUNNABLE / UNRUNNABLE + why
python3 scripts/bench_board.py orin                          # bench the board's default 7B rung
python3 scripts/bench_board.py orin --provision qwen2.5-14b  # gate -> download -> stage -> bench a 14B
python3 scripts/aggregate_boards.py                          # combine every board into one ladder
```

Each run writes a standard JSON to `eval/results/ladder/board_runs/`. A provisioned model gets its own file (`orin@qwen2.5-14b.json`), so it never overwrites the board's 7B result. Board setup: [`docs/RUN_BOARDS.md`](docs/RUN_BOARDS.md).

## Grade accuracy (optional)

```bash
python3 scripts/x86_demo.py --tasks                     # produce task outputs
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=...         # grader only; the benchmark needs no keys
python3 eval/judge_agentic_tasks.py
```

---

## How the numbers stay honest

| Tag | Meaning |
|---|---|
| **MEASURED** | We ran it, on this hardware. The only kind that appears bare or in a headline. |
| **DERIVED** | Computed from measurements (e.g. bandwidth = decode × weight bytes). Always labelled. |
| **SOURCED** | From a vendor datasheet or the literature. Labelled, and used only where we couldn't measure. |

- A derived or sourced number is never compared head-to-head with a measured one.
- Model size stays in view: 3B and 7B rows aren't compared directly.
- A broken output is cheaper to generate, so its timing doesn't count.
- Corrections are logged in [`docs/RESULTS.md`](docs/RESULTS.md).

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
  test_catalog.json    # the 10-task agentic catalog
  judge_agentic_tasks.py  # optional two-judge accuracy grader
  results/             # measured results (the ladder + per-board runs)
docs/
  RUN_X86_DEMO.md      # the laptop demo, in depth
  RUN_BOARDS.md        # running the ladder on your own boards
  RESULTS.md           # measured ladder + methodology
.github/workflows/
  x86-demo.yml         # runs the laptop demo on Windows + Linux on every change
```

## Requirements

- Python 3.9+
- `llama-cpp-python` and `huggingface-hub` for the laptop demo (CPU wheel, no compiler)
- For boards: a `llama.cpp` build on each board, reachable over SSH
- For grading (optional): `anthropic`, `openai` and their API keys

```bash
pip install -r requirements.txt
```

## License

MIT. See [`LICENSE`](LICENSE).
