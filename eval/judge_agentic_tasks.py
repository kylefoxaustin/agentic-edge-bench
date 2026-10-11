#!/usr/bin/env python3
"""Two-judge (cross-family) accuracy grading of the agentic task outputs — OPTIONAL.

The resource benchmark (decode ladder, x86 demo) measures *cost*; this measures *correctness*,
a separate axis. It grades each task output PASS / PARTIAL / FAIL with TWO independent judges
from different model families — Claude (Anthropic) + GPT-4o (OpenAI) — so a result doesn't ride
on one model's blind spots. Both judges run at temperature 0 (deterministic); disagreements are
FLAGGED, never averaged.

By default it grades the outputs produced by `x86_demo.py --tasks` (read from the demo's result
JSON). Needs ANTHROPIC_API_KEY + OPENAI_API_KEY (see eval/_keys.py). `--dry-run` prints the
prompts without calling any API.

    python3 eval/judge_agentic_tasks.py                         # grade the latest x86 --tasks run
    python3 eval/judge_agentic_tasks.py --input path/to.json     # a specific result JSON
    python3 eval/judge_agentic_tasks.py --dry-run
"""
import argparse, glob, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X86_RESULT = os.path.join(REPO, "eval/results/ladder/board_runs/localhost-x86.json")
HARNESS_DIR = os.path.join(REPO, "eval/results/ladder/agentic")

# Ground truth for the bundled i.MX95 example tasks. Replace this (and the task prompts) with your
# own domain's facts to grade your own tasks.
GROUND_TRUTH = (
    "NXP i.MX 95 datasheet facts: 6x Arm Cortex-A55 + Cortex-M33 + Cortex-M7; eIQ Neutron NPU "
    "(N3-1024S) rated 2.0 TOPS = 1024 MACs x 1.0 GHz x 2 OPS/MAC; Mali GPU; ISP; LPDDR5X memory; "
    "PCIe Gen3; Gigabit-Ethernet TSN; Energy Flex architecture. Targets automotive/industrial/"
    "consumer edge AI. NOT true: 'Neutrino' NPU, dual-A55-only, LPDDR4X, 16GB, custom-PCB-Q4-2023."
)
RUBRIC = {
 "email": "Draft a coherent, friendly email introducing the i.MX 95 for an edge-AI product, covering what it is, the Neutron NPU, and why it suits edge. PASS = coherent email, specifics grounded in the facts, no fabricated specs.",
 "file_ops": "Read notes and summarize them in 3 bullets. PASS = accurate bullet summary grounded in the notes, no fabrication.",
 "spec_inline": "Answer what the i.MX 95 Neutron NPU does and its key rated specs, grounded ONLY in the provided context. PASS = accurate (2.0 TOPS / 1024 MAC@1GHz) and grounded, no fabrication.",
 # harness tasks (if grading a full-harness run instead of the x86 demo):
 "spec_rag": "Answer what the i.MX 95 Neutron NPU does and its key features from retrieved datasheets. PASS = accurate (2.0 TOPS / 1024 MAC@1GHz) and grounded, no fabrication.",
}
JUDGE_INSTRUCTIONS = (
 "You are grading whether a local AI assistant completed an agentic task. Grade ONLY task success "
 "and factual correctness (not style). Return STRICT JSON only: "
 '{\"verdict\": \"PASS\"|\"PARTIAL\"|\"FAIL\", \"reason\": \"<one sentence>\"}. '
 "PARTIAL = did the task but with a material flaw (generic/content-free, or fabricated a sub-part). "
 "FAIL = did not accomplish the task or fabricated the core answer."
)

def load_outputs(input_path):
    """Return {task_id: output_text}. Prefers an x86 --tasks result (quick_tasks array); falls
    back to the newest bench_<task>_*.json in the harness dir."""
    path = input_path or (X86_RESULT if os.path.exists(X86_RESULT) else None)
    if path and os.path.exists(path):
        data = json.load(open(path))
        if "quick_tasks" in data:
            return {t["id"]: t.get("output", "") for t in data["quick_tasks"]}
    # harness fallback
    out = {}
    for t in RUBRIC:
        fs = sorted(glob.glob(f"{HARNESS_DIR}/bench_{t}_*.json"))
        if fs:
            out[t] = json.load(open(fs[-1])).get("output", "")
    return out

def build_user_prompt(task, output):
    rub = RUBRIC.get(task, "Complete the task correctly and without fabrication.")
    return (f"GROUND TRUTH: {GROUND_TRUTH}\n\nTASK: {task}\nWHAT PASS REQUIRES: {rub}\n\n"
            f"ASSISTANT OUTPUT:\n\"\"\"\n{output[:2500]}\n\"\"\"\n\nGrade it. STRICT JSON only.")

def parse_verdict(text):
    m = re.search(r'\{.*\}', text, re.S)
    if not m: return {"verdict": "?", "reason": f"unparseable: {text[:120]}"}
    try:
        d = json.loads(m.group(0)); d["verdict"] = str(d.get("verdict", "?")).upper(); return d
    except Exception as e:
        return {"verdict": "?", "reason": f"parse error: {e}"}

def judge_anthropic(task, output, model):
    from anthropic import Anthropic
    c = Anthropic()
    r = c.messages.create(model=model, max_tokens=300, temperature=0, system=JUDGE_INSTRUCTIONS,
                          messages=[{"role": "user", "content": build_user_prompt(task, output)}])
    return parse_verdict(r.content[0].text)

def judge_openai(task, output, model):
    from openai import OpenAI
    c = OpenAI()
    r = c.chat.completions.create(model=model, max_tokens=300, temperature=0,
        messages=[{"role": "system", "content": JUDGE_INSTRUCTIONS},
                  {"role": "user", "content": build_user_prompt(task, output)}])
    return parse_verdict(r.choices[0].message.content)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anthropic-model", default="claude-sonnet-4-6")
    ap.add_argument("--openai-model", default="gpt-4o")
    ap.add_argument("--input", help="result JSON to grade (default: the latest x86 --tasks run)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=f"{HARNESS_DIR}/task_success_twojudge.json")
    a = ap.parse_args()

    outputs = load_outputs(a.input)
    if not outputs:
        sys.exit("No task outputs found. Run  python3 scripts/x86_demo.py --tasks  first "
                 "(or pass --input <result.json>).")
    if a.dry_run:
        for t, o in outputs.items():
            print(f"\n===== {t} =====\n{build_user_prompt(t, o)[:600]}")
        return

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _keys import ensure_keys
    missing = ensure_keys(("ANTHROPIC_API_KEY", "OPENAI_API_KEY"))
    if missing:
        sys.exit(f"ERROR: {', '.join(missing)} not set. Put them in ~/.agentic-edge-bench/keys.env "
                 f"(KEY=VALUE lines) or export them. Only the grader needs keys.")

    results, tally = {}, {"agree": 0, "split": 0}
    for t, out in outputs.items():
        try: sv = judge_anthropic(t, out, a.anthropic_model)
        except Exception as e: sv = {"verdict": "ERR", "reason": str(e)[:120]}
        try: gv = judge_openai(t, out, a.openai_model)
        except Exception as e: gv = {"verdict": "ERR", "reason": str(e)[:120]}
        agree = sv.get("verdict") == gv.get("verdict")
        tally["agree" if agree else "split"] += 1
        results[t] = {"claude": sv, "gpt4o": gv, "agree": agree}
        print(f"  {t:14s} claude={sv.get('verdict'):8s} gpt4o={gv.get('verdict'):8s} {'AGREE' if agree else '<<SPLIT>>'}")

    summary = {"judges": {"anthropic": a.anthropic_model, "openai": a.openai_model},
               "rule": "two judges, different families; both read; splits flagged not averaged; temp 0",
               "agreement": tally, "results": results}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(summary, open(a.out, "w"), indent=2)
    print(f"\n  wrote {os.path.relpath(a.out, REPO)}  ·  agree={tally['agree']} split={tally['split']}")

if __name__ == "__main__":
    main()
