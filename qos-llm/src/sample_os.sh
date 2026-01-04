#!/usr/bin/env bash
set -euo pipefail

PID="${1:?usage: sample_os.sh <pid> <csv_out> [interval_seconds]}"
OUT="${2:?usage: sample_os.sh <pid> <csv_out> [interval_seconds]}"
INTERVAL="${3:-0.5}"

echo "ts,rss_mb,cpu_pct,vm_pressure_flag,avail_mem_level,pageins_delta,pageouts_delta" > "$OUT"

get_vm_counters() {
    local pi po
    pi=$(vm_stat | awk '/Pageins/ {gsub("\\.","",$2); print $2}' | head -n1)
    po=$(vm_stat | awk '/Pageouts/ {gsub("\\.","",$2); print $2}' | head -n1)
    echo "${pi:-0} ${po:-0}"
}

get_vm_pressure_flag() {
    # 1=normal, 2=warning, 4=critical (may be empty on some systems)
    sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null || echo ""
}

get_avail_mem_level() {
    # Often treated as a percent-like indicator in tooling; may be empty on some systems
    sysctl -n kern.memorystatus_level 2>/dev/null || echo ""
}

read PI0 PO0 < <(get_vm_counters)

while kill -0 "$PID" 2>/dev/null; do
    TS=$(python3 -c 'import time; print(time.time())')
    
    RSS_KB=$(ps -o rss= -p "$PID" | awk '{print $1}' || echo 0)
    CPU=$(ps -o %cpu= -p "$PID" | awk '{print $1}' || echo 0)
    RSS_MB=$(awk -v kb="$RSS_KB" 'BEGIN { printf "%.2f", kb/1024.0 }')
    
    PRESS_FLAG=$(get_vm_pressure_flag)
    AVAIL_LVL=$(get_avail_mem_level)
    
    read PI PO < <(get_vm_counters)
    PI_D=$((PI - PI0))
    PO_D=$((PO - PO0))
    
    echo "$TS,$RSS_MB,$CPU,$PRESS_FLAG,$AVAIL_LVL,$PI_D,$PO_D" >> "$OUT"
    sleep "$INTERVAL"
done

