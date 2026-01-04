#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

RE_TPUT = re.compile(r"\[\s*Prompt:\s*([0-9.]+)\s*t/s\s*\|\s*Generation:\s*([0-9.]+)\s*t/s\s*\]")
RE_METAL = re.compile(
    r"Metal .*?\|\s*12288\s*=\s*([0-9]+)\s*\+\s*\(([0-9]+)\s*=\s*([0-9]+)\s*\+\s*([0-9]+)\s*\+\s*([0-9]+)\)\s*\+\s*([0-9]+)"
)

def read_text(p: Path) -> str:
    return p.read_text(errors="ignore")

def parse_log(log_text: str) -> dict:
    out = {}

    # Throughput (last match)
    tputs = RE_TPUT.findall(log_text)
    if tputs:
        prompt_ts, gen_ts = tputs[-1]
        out["prompt_tps"] = float(prompt_ts)
        out["gen_tps"] = float(gen_ts)

    # Metal breakdown (last match)
    # groups: free, used_total, model, context, compute, unaccounted
    metals = RE_METAL.findall(log_text)
    if metals:
        free, used_total, model, context, compute, unacc = metals[-1]
        out["metal_free_mib"] = int(free)
        out["metal_used_mib"] = int(used_total)
        out["metal_model_mib"] = int(model)
        out["metal_context_mib"] = int(context)
        out["metal_compute_mib"] = int(compute)
        out["metal_unaccounted_mib"] = int(unacc)

    return out

def parse_config(cfg_path: Path) -> dict:
    cfg = {}
    for line in cfg_path.read_text(errors="ignore").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg

def main(run_dir: str):
    run = Path(run_dir)
    log_path = run / "llama_output.log"
    cfg_path = run / "config.txt"
    out_path = run / "summary.json"

    if not log_path.exists():
        raise SystemExit(f"missing {log_path}")
    if not cfg_path.exists():
        raise SystemExit(f"missing {cfg_path}")

    cfg = parse_config(cfg_path)
    log_text = read_text(log_path)
    parsed = parse_log(log_text)

    summary = {
        "run_dir": str(run.resolve()),
        "tag": cfg.get("tag", ""),
        "ctx": int(cfg.get("ctx", "0") or 0),
        "gen_tokens": int(cfg.get("gen_tokens", "0") or 0),
        "model_path": cfg.get("model", ""),
        **parsed,
    }

    out_path.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: parse_run.py <runs/<RUN_ID>>")
    main(sys.argv[1])