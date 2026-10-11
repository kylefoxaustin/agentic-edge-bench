# Run the Agentic-Edge Demo on Your Own x86 Laptop (pure CPU)

**Goal: clone the repo, run one command, and reproduce the headline finding on your own
machine — no GPU, no Docker, no server, no fleet.** It downloads a small model, runs a
CPU decode benchmark, and shows you that

> **decode (token generation) is bounded by your DDR memory bandwidth, not by compute/TOPS.**

Works on **Linux** (native) and **Windows** (native or WSL2). Intel or AMD x86. A laptop is fine.

---

## 1. Install (one wheel)

You need Python 3.9+ and `llama-cpp-python` (the same CPU runtime the project uses). No CUDA.

**Linux / WSL2:**
```bash
pip install llama-cpp-python
```

**Windows (native):** easiest is a prebuilt CPU wheel (no compiler needed):
```powershell
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```
(If you prefer to build from source on Windows you'll need the "Desktop development with C++"
Visual Studio Build Tools. The prebuilt wheel above skips that.)

> **Windows tip:** WSL2 (Ubuntu) is the smoothest path and matches the Linux instructions exactly.
> Native Windows works too via the prebuilt wheel.

## 2. Run

```bash
python3 scripts/x86_demo.py                 # default: Qwen2.5-3B (2 GB, laptop-friendly)
```

That's it. The script self-downloads the GGUF from Hugging Face on first run (cached afterward),
checks it fits in your RAM, and benchmarks prefill + decode on your CPU.

Options:
```bash
python3 scripts/x86_demo.py --model 7b        # the ladder's reference size (needs ~6 GB free RAM)
python3 scripts/x86_demo.py --threads 8        # override thread count (default: physical-core-ish)
python3 scripts/x86_demo.py --ddr-gbps 89.6    # supply your peak DDR bandwidth for the util% headline
python3 scripts/x86_demo.py --tasks            # also run 3 real agentic tasks (see below)
```

### `--tasks` — run real agentic work, model only

The default run is a raw decode/prefill micro-benchmark (the bandwidth headline). `--tasks` adds
three **real** agentic tasks that need **nothing but the loaded model** — no server, no ChromaDB,
no network, no extra pip installs:

1. **Email drafting** — pure generation.
2. **File read + summarize** — reads a bundled local notes file → 3 bullets (a file-tool + decode).
3. **Grounded spec Q&A (inline context)** — the datasheet facts are pasted into the prompt instead
   of retrieved, so it's grounded *without* a vector DB ("poor-man's RAG").

Each prints its output (read it — the coherence gate) plus a **DERIVED decode-share**: the
prefill/decode time split estimated from the measured rates. You'll see every task is
**70–90%+ decode** — i.e. even real agentic prompts are bandwidth-bound, which is the whole point.

> **What you'll notice on the 3B:** the grounded Q&A is accurate (the facts are right there), the
> email is coherent, and the file-summary may **fabricate** details not in the notes. That's not a
> demo glitch — it's the finding: a small model's accuracy is bounded by *grounding*, not size.
> `--model 7b` grounds noticeably better. The other 7 tasks of the full benchmark (RAG, ASR, OCR,
> web, tool-chains) need infrastructure (a vector DB, Whisper, Tesseract, a tool-calling agent loop)
> and aren't part of this model-only demo.

## 3. Read the result

Example (a real run on an Intel i9-14900KF desktop, dual-channel DDR5-5600):
```
=== x86/AMD pure-CPU decode-ladder demo ===
  CPU      : Intel(R) Core(TM) i9-14900KF  (32 logical cores, using 16 threads)
  SIMD     : AVX2, AVX, FMA, F16C  (llama.cpp build — prefill speed depends on this)
  RAM      : 101.0 GB
  DDR peak : 89.6 GB/s (user-supplied)  [SOURCED]
  model    : qwen2.5-3b  (Q4_K_M, 2.0 GB weights, 3.1B params)
  gate     : RUNNABLE — fits: needs ~3.5 GB, box has 101.0 GB

  --- result ---
  prefill        :    228.4 tok/s   [MEASURED]  (compute-bound; scales with --threads)
  decode         :    32.95 tok/s   [MEASURED]  (bandwidth-bound; ~flat vs threads)
  eff. mem BW    :     65.9 GB/s    [DERIVED: decode x weights]
  DDR util       :     73.5 %       [DERIVED/SOURCED] <- decode runs at 73.5% of peak DDR BW

  ==> Decode is memory-bandwidth-bound: the generation loop sustains 73.5% of this box's
      peak DDR bandwidth with ZERO GPU/NPU. More TOPS would not move this number; more
      memory bandwidth (faster/more DIMM channels) would.
```
Your numbers will differ — that's the point; report your own CPU + DDR + date.

**What the numbers mean**
- **decode tok/s** — how fast it generates. This is what you feel in an interactive agent.
- **eff. mem BW** = `decode_tok/s x model_weight_bytes`. A dense model reads ~all its weights
  from DRAM once per generated token, so this is the memory bandwidth the decode loop actually
  pulls. It's a **DERIVED** number (labelled as such).
- **DDR util %** — that effective bandwidth as a fraction of your DIMMs' peak. On most laptops
  decode lands at **60–90% of peak DDR**, which is the finding: *the generation loop is fed by
  memory bandwidth, and an accelerator's TOPS are idle during it.*

### Provenance (why the labels)
Per the project's Fleet Law 1, every number carries a tag:
- `decode` / `prefill` tok/s → **MEASURED** (ran on your box).
- `eff. mem BW` → **DERIVED** (decode × weights).
- `DDR peak` → **SOURCED** (your DIMM speed, auto-detected or `--ddr-gbps`).

The honest headline is the **within-box util %** — a derived/sourced ratio of your own machine.
Don't compare your laptop's derived effective-BW bare against another board's measured tok/s;
that's a mixed-tier comparison. Compare decode tok/s to decode tok/s.

## 4. (Optional) see it in the cross-board ladder

```bash
python3 scripts/aggregate_boards.py
```
Your `localhost-x86` rung is written to `eval/results/ladder/board_runs/localhost-x86.json` and
joins the ladder next to the Jetsons / i.MX95 rungs (where those runs exist).

---

## Scope

This demo is the **x86 laptop tier** — it reproduces the bandwidth finding with the least setup,
plus the three model-only tasks above. To run the same decode ladder on an edge board (Jetson,
i.MX95, etc.) over SSH, see [`RUN_BOARDS.md`](RUN_BOARDS.md). The full infrastructure-heavy agentic
harness (RAG / ASR / OCR / web / tool-chains) is out of scope for this repo — it needs a running
LLM server and a vector DB.

## Troubleshooting
- **`llama-cpp-python is not installed`** — see step 1. On Windows use the prebuilt-wheel index.
- **`UNRUNNABLE — won't fit`** — the model is bigger than your free RAM. Use `--model 3b` (default)
  or close other apps. The gate refuses rather than thrash swap.
- **`DDR peak: unknown`** — auto-detect needs `sudo dmidecode` (Linux) or `wmic` (Windows). Pass
  `--ddr-gbps <peak>` to get the util% (peak = channels × MT/s × 8 ÷ 1000; e.g. dual-channel
  DDR5-5600 = 2×5600×8÷1000 ≈ 89.6 GB/s).
- **Download is slow / offline** — the GGUF comes from Hugging Face on first run and is cached. On
  a metered/offline box, pre-download it once on a connected machine (same HF repo in
  `eval/model_registry.json`).
