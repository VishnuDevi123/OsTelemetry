# OsTelemetry: llama.cpp Quantization Study

Personal study focused on performance and memory tradeoffs between quantized GGUF models  
(Q4 vs Q8) on macOS with Apple Silicon and Metal acceleration.

## 1. Overview

This project explores inference QoS characteristics for quantized large language models using `llama.cpp` on macOS.  
The focus is on **practical system behavior**.
Key questions I asked myself:
- Does the model fit in unified memory at a given context length (`ctx`)?
- What is the token generation throughput (tokens/sec)?
- How does paging and memory pressure behave across multiple runs with/without other smaller process in the background?


## 2. What Is Tracked

### Per-run artifacts
- `llama_output.log`  
  Model output, `--perf` stats, Metal memory breakdown
- `metrics.csv`  
  Sampled OS telemetry (RSS, CPU, paging, VM pressure)
- `config.txt`  
  Model path, context size, generation tokens, run tag

### OS telemetry fields (`metrics.csv`)

| Metric | Description | Usage |
|------|------------|------|
| `ts` | Timestamp (seconds since epoch) | Align load, generation, teardown |
| `rss_mb` | Resident memory for sampled PID | Phase-level trends only |
| `cpu_pct` | CPU utilization (%) | CPU-side work alongside Metal |
| `vm_pressure_flag` | 1 = normal · 2 = warning · 4 = critical | System-wide memory stress |
| `avail_mem_level` | macOS memory availability scalar | OS reclaim / compression behavior |
| `pageins_delta` | Pages loaded from disk → RAM | Detects faulting |
| `pageouts_delta` | Pages evicted from RAM → disk | Detects eviction |


## 3. Current Progress

### Harness & Telemetry
- Automated, non-interactive runs
- OS telemetry sampling for memory and CPU
- Stable single-turn inference capture

### Q4 vs Q8 Comparison
- Parsed throughput from `--perf`
- Extracted Metal memory breakdown
- Summarized runtime, paging, and CPU usage


## 4. Latest Comparison

**Context:** 4096  
**Generation tokens:** 256

### Throughput & runtime

| Model | Prompt TPS | Generation TPS | Duration (s) | Notes |
|-----|-----------|---------------|-------------|------|
| Q4 (Q4_K_M) | 16312.7 | **26.6** | **15.26** | Faster generation |
| Q8 (Q8_0) | 15393.6 | 16.4 | 24.03 | Slower under same settings |

### Metal / host memory breakdown

| Model | Metal Used (MiB) | Model (MiB) | Context (MiB) | Compute (MiB) | Host (MiB) |
|-----|-----------------|-------------|---------------|---------------|------------|
| Q4 | 5455 | **4685** | 512 | 258 | 297 |
| Q8 | **8908** | **8137** | 512 | 258 | 548 |


## 5. Interpretation Notes

### RSS vs actual model footprint
- RSS shows **CPU-visible resident pages only** or in simpler terms only the onces that are held in the memory(RAM) and the others are sort of swapped out to disk
- Metal allocations live in **GPU-managed unified memory**
- Use llama.cpp Metal breakdown for capacity planning
- Use RSS mainly for phase detection

### Why macOS memory usage shifts across runs
- macOS aggressively compresses and reclaims memory
- Large allocations trigger cache purging and diskswaping
- Single runs are super noise, but when multiple runs are made accross, there is a change in trend


## 6. Reproduce

```bash
./src/run_os.sh models/llama3.1-8b-instruct-q4_k_m.gguf 4096 256 q4_capture
./src/run_os.sh models/llama3.1-8b-instruct-q8_0.gguf   4096 256 q8_capture