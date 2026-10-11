# Running the decode ladder on your own boards

The x86 demo ([`RUN_X86_DEMO.md`](RUN_X86_DEMO.md)) runs on the machine you're sitting at. To add
edge boards to the ladder — a Jetson, an i.MX, or any SSH-reachable Linux box with `llama.cpp` —
use the per-board driver. Same instrument everywhere; only the per-board *runtime* differs.

## Model shape — the one thing to keep straight

The ladder compares boards at the **same model size**. Decode cost scales ~linearly with model
size (it's bandwidth: more weight bytes per token), so a 3B rung and a 7B rung are not comparable.
Keep the model fixed across the boards you compare, and label the size on every rung. (In the
bundled results the ladder is 7B except where a rung is marked 3B.)

## Prerequisites per board

1. **SSH reachable.** An entry in your `~/.ssh/config` so `ssh <alias>` works passwordlessly.
2. **A `llama.cpp` build on the board** with `llama-bench`:
   - NVIDIA Jetson: build with CUDA for the board's arch (`-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=<87|110|…>`).
   - CPU boards: a plain CPU build.
3. **The GGUF staged** on the board (the driver can stage it for you — see provisioning).

## Define your board

Boards live in two places; add your board to both:

- `eval/model_registry.json` → `boards` — for the feasibility gate (RAM, runtime, arch support).
- `scripts/bench_board.py` → `BOARDS` — the SSH alias, the `llama-bench` path, and the model path
  on the board. Example entry:

```python
 "mybox": dict(res="mybox", ssh="mybox", backend="cuda",
               bin="~/llama.cpp/build/bin/llama-bench",
               model="~/models/qwen2.5-7b-instruct-q4_k_m.gguf", args="-ngl 99"),
```

`backend` picks the adapter: `cuda` / `cpu` (both llama.cpp llama-bench), or the vendor adapters
`kinara-ara2` and `genie-stub` for the accelerators they name.

## The feasibility gate — "can this board run this model?"

Before downloading or running anything, answer whether it *fits*:

```bash
python3 scripts/provision.py mybox qwen2.5-7b --check-only   # RUNNABLE / UNRUNNABLE + why
python3 scripts/provision.py mybox qwen2.5-7b                # gate -> download from HF -> scp to board
python3 scripts/provision.py --list                         # models + boards
```

The gate checks memory fit (weights + KV headroom vs board RAM) and runtime/arch support, and
refuses with a reason (`UNRUNNABLE — won't fit: ~12 GB > 8 GB`) rather than failing obscurely.

## Bench a board

```bash
python3 scripts/bench_board.py mybox        # census -> stage if missing -> llama-bench -> write JSON
python3 scripts/bench_board.py mybox --provision qwen2.5-7b   # gate + provision first
python3 scripts/bench_board.py orin --rebuild                  # rebuild llama.cpp if it segfaults (driver drift)
```

Each run writes `eval/results/ladder/board_runs/<board>.json` with decode/prefill tok/s, a census
(was anything else hammering the board?), and the backend. **Read it** — apply the coherence gate:
a broken or truncated output is a cheaper, unrepresentative computation, so its numbers don't count.

> **Optional contention guard.** If you run a shared fleet and have a reservation CLI, set
> `BENCH_RESERVE_CMD=/path/to/your-reserve-tool` and the driver will reserve/release the board
> around the run (`<cmd> res reserve <board> 90m hard` / `<cmd> res release <board>`). On a single
> board it's simply absent and benching proceeds unguarded.

## Combine into the ladder

```bash
python3 scripts/aggregate_boards.py
```

Reads every `board_runs/*.json` and prints the comparable decode/prefill ladder, each rung tagged
by backend + provenance, and writes `eval/results/ladder/board_runs/_ladder.json`.

## Vendor-accelerator notes

- **Kinara Ara-2 (`kinara-ara2`)** exposes *independent* endpoints: a 2nd Ara roughly doubles
  aggregate throughput, not single-query latency. The on-SoC NPU is a separate prefill/TTFT engine.
- **Qualcomm Hexagon / Genie (`genie-stub`)** uses QNN `.bin` artifacts with a prompt-length cap;
  the adapter here records a vendor-sourced point — wire in your own Genie toolchain to re-measure.

These adapters are examples from the hardware this was developed on; adapt them to your silicon.
