#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt

def load_metrics(csv_path: Path):
    rows = []
    with csv_path.open() as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append({
                "ts": float(row["ts"]),
                "rss_mb": float(row["rss_mb"]),
                "cpu_pct": float(row["cpu_pct"]),
                "vm_pressure_flag": row.get("vm_pressure_flag", ""),
                "avail_mem_level": row.get("avail_mem_level", ""),
                "pageins_delta": float(row["pageins_delta"]),
                "pageouts_delta": float(row["pageouts_delta"]),
            })
    return rows

def to_rel_time(rows):
    if not rows:
        return rows
    t0 = rows[0]["ts"]
    for r in rows:
        r["t_rel"] = r["ts"] - t0
    return rows

def summarize_metrics(rows):
    rss = [r["rss_mb"] for r in rows]
    cpu = [r["cpu_pct"] for r in rows]
    pouts = [r["pageouts_delta"] for r in rows]
    pins = [r["pageins_delta"] for r in rows]
    return {
        "rss_peak_mb": max(rss) if rss else 0.0,
        "rss_mean_mb": mean(rss) if rss else 0.0,
        "cpu_mean_pct": mean(cpu) if cpu else 0.0,
        "pageins_final": pins[-1] if pins else 0.0,
        "pageouts_final": pouts[-1] if pouts else 0.0,
        "duration_s": rows[-1]["t_rel"] if rows else 0.0,
    }

def save_plot(x, y, xlabel, ylabel, title, out_path: Path):
    plt.figure()
    plt.plot(x, y)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

def analyze_run(run_dir: Path, report_dir: Path):
    metrics_path = run_dir / "metrics.csv"
    summary_path = run_dir / "summary.json"

    rows = to_rel_time(load_metrics(metrics_path))
    metric_summary = summarize_metrics(rows)

    base = json.loads(summary_path.read_text())
    merged = {**base, **metric_summary}

    report_dir.mkdir(parents=True, exist_ok=True)

    # Save merged summary
    (report_dir / f"{run_dir.name}_summary.json").write_text(json.dumps(merged, indent=2))

    # Plots
    t = [r["t_rel"] for r in rows]
    save_plot(t, [r["rss_mb"] for r in rows], "time (s)", "rss (MB)",
              f"RSS vs time ({run_dir.name})", report_dir / f"{run_dir.name}_rss.png")
    save_plot(t, [r["cpu_pct"] for r in rows], "time (s)", "cpu (%)",
              f"CPU% vs time ({run_dir.name})", report_dir / f"{run_dir.name}_cpu.png")
    save_plot(t, [r["pageouts_delta"] for r in rows], "time (s)", "pageouts (delta)",
              f"Pageouts vs time ({run_dir.name})", report_dir / f"{run_dir.name}_pageouts.png")

    return merged

def main(dirs):
    runs = [Path(d) for d in dirs]
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)

    merged = [analyze_run(r, report_dir) for r in runs]

    # Write a simple comparison JSON
    (report_dir / "comparison.json").write_text(json.dumps(merged, indent=2))

    # Print a compact table to stdout
    print("\nComparison:")
    for m in merged:
        print(
            f"- {m.get('tag','')}  ctx={m.get('ctx')}  "
            f"gen_tps={m.get('gen_tps','?')}  "
            f"metal_model_mib={m.get('metal_model_mib','?')}  "
            f"rss_peak_mb={m.get('rss_peak_mb',0):.2f}  "
            f"pageouts_final={m.get('pageouts_final',0)}"
        )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: analyze_runs.py <run_dir1> <run_dir2> ...")
    main(sys.argv[1:])