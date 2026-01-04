<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OsTelemetry + llama.cpp QoS Bench</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; line-height: 1.45; margin: 24px; max-width: 1040px; }
    code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    pre { background: #f6f8fa; padding: 12px; border-radius: 8px; overflow: auto; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .card { border: 1px solid #ddd; border-radius: 10px; padding: 14px; }
    .muted { color: #555; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
    th { background: #f3f4f6; text-align: left; }
    ul { margin-top: 6px; }
    h1, h2, h3 { margin-top: 22px; }
    .kbd { border: 1px solid #bbb; border-bottom-width: 2px; padding: 0 6px; border-radius: 6px; background: #fff; }
    .good { font-weight: 600; }
    .warn { font-weight: 600; }
    .tiny { font-size: 0.95em; }
  </style>
</head>
<body>

  <header>
    <h1>OsTelemetry: llama.cpp Quantization QoS Benchmark (macOS + Metal)</h1>
    <p class="muted">
      Goal: measure performance + memory tradeoffs between quantized GGUF models (Q4 vs Q8) on Apple Silicon (Metal backend).
    </p>
  </header>

  <section>
    <h2>1) Introduction</h2>
    <p>
      This project benchmarks inference QoS characteristics for quantized LLMs running via <code>llama.cpp</code> on macOS
      with Metal acceleration. Quantization impacts:
    </p>
    <ul>
      <li>Whether a model fits in unified memory at target context length (<code>ctx</code>)</li>
      <li>Token generation throughput (tokens/sec)</li>
      <li>System-level paging pressure under repeated runs</li>
    </ul>
  </section>

  <section>
    <h2>2) What I Track</h2>
    <h3>Per-run artifacts</h3>
    <ul>
      <li><code>llama_output.log</code>: model output + <code>--perf</code> throughput + Metal memory breakdown</li>
      <li><code>metrics.csv</code>: sampled OS metrics (RSS/CPU + paging deltas + VM pressure flags)</li>
      <li><code>config.txt</code>: model path, ctx, gen tokens, prompt file, tag</li>
    </ul>

    <h3>OS Metrics (metrics.csv)</h3>
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>Meaning</th>
          <th>How to interpret here</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>ts</code></td>
          <td>Timestamp (seconds since epoch, float)</td>
          <td>Align phases: load vs generation vs teardown.</td>
        </tr>
        <tr>
          <td><code>rss_mb</code></td>
          <td>Resident memory attributed to the sampled PID</td>
          <td>Useful for trend/phase detection; not a complete view of Metal/unified allocations.</td>
        </tr>
        <tr>
          <td><code>cpu_pct</code></td>
          <td>CPU utilization (%) for sampled PID</td>
          <td>Shows CPU work (tokenization, scheduling, some compute) alongside Metal compute.</td>
        </tr>
        <tr>
          <td><code>vm_pressure_flag</code></td>
          <td><code>kern.memorystatus_vm_pressure_level</code> (1=normal, 2=warning, 4=critical)</td>
          <td>System-wide signal; useful to detect memory stress events during runs.</td>
        </tr>
        <tr>
          <td><code>avail_mem_level</code></td>
          <td><code>kern.memorystatus_level</code> (scalar often shown like a %)</td>
          <td>Another system-wide memory signal; shifts as macOS reclaims/compresses memory.</td>
        </tr>
        <tr>
          <td><code>pageins_delta</code></td>
          <td>Increase in pageins since run start</td>
          <td>Higher deltas can indicate disk-to-RAM activity.</td>
        </tr>
        <tr>
          <td><code>pageouts_delta</code></td>
          <td>Increase in pageouts since run start</td>
          <td>Higher deltas can indicate eviction to disk under memory pressure.</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>3) Current Progress</h2>
    <div class="grid">
      <div class="card">
        <h3>Milestone 1: Harness + Telemetry</h3>
        <ul>
          <li>Automated runs with fixed <code>ctx</code> and token budget (<code>src/run_os.sh</code>).</li>
          <li>OS sampling for RSS/CPU + VM pressure + paging deltas (<code>src/sample_os.sh</code>).</li>
          <li>Non-interactive run stability using single-turn mode and output capture.</li>
        </ul>
      </div>
      <div class="card">
        <h3>Milestone 2: Q4 vs Q8 Comparison</h3>
        <ul>
          <li>Extracted TPS from <code>--perf</code> output.</li>
          <li>Extracted Metal memory breakdown (model/context/compute).</li>
          <li>Summarized peak RSS, mean RSS, mean CPU, paging deltas, and duration.</li>
        </ul>
      </div>
    </div>
  </section>

  <section>
    <h2>4) Latest Runs Compared (ctx=4096, gen_tokens=256)</h2>
    <p class="muted tiny">
      Runs used:
      <br />
      Q4: <code>/runs/2025-12-23T19-36-05_q4_capture_ctx4096</code>
      <br />
      Q8: <code>/runs/2025-12-23T19-36-26_q8_capture_ctx4096</code>
    </p>

    <h3>Throughput + Runtime</h3>
    <table>
      <thead>
        <tr>
          <th>Model</th>
          <th>Prompt TPS</th>
          <th>Generation TPS</th>
          <th>Duration (s)</th>
          <th>Takeaway</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>llama3.1-8b-instruct-q4_k_m.gguf</code></td>
          <td>16312.7</td>
          <td class="good">26.6</td>
          <td class="good">15.255</td>
          <td>Faster generation and shorter end-to-end run time.</td>
        </tr>
        <tr>
          <td><code>llama3.1-8b-instruct-q8_0.gguf</code></td>
          <td>15393.6</td>
          <td>16.4</td>
          <td>24.034</td>
          <td>Slower generation; longer run time at same settings.</td>
        </tr>
      </tbody>
    </table>

    <h3>Metal / Host Memory Breakdown (from llama.cpp)</h3>
    <table>
      <thead>
        <tr>
          <th>Model</th>
          <th>Metal Used (MiB)</th>
          <th>Metal Free (MiB)</th>
          <th>Model (MiB)</th>
          <th>Context (MiB)</th>
          <th>Compute (MiB)</th>
          <th>Host (MiB)</th>
          <th>Takeaway</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Q4 (Q4_K_M)</td>
          <td>5455</td>
          <td class="good">6830</td>
          <td class="good">4685</td>
          <td>512</td>
          <td>258</td>
          <td>297</td>
          <td>Lower model footprint; more headroom for other apps or larger ctx.</td>
        </tr>
        <tr>
          <td>Q8 (Q8_0)</td>
          <td class="warn">8908</td>
          <td>3378</td>
          <td class="warn">8137</td>
          <td>512</td>
          <td>258</td>
          <td>548</td>
          <td>Model footprint dominates; higher risk of memory pressure at larger ctx.</td>
        </tr>
      </tbody>
    </table>

    <h3>OS Telemetry Summary (RSS/CPU/Paging)</h3>
    <table>
      <thead>
        <tr>
          <th>Model</th>
          <th>RSS Peak (MB)</th>
          <th>RSS Mean (MB)</th>
          <th>CPU Mean (%)</th>
          <th>Pageins Final</th>
          <th>Pageouts Final</th>
          <th>Takeaway</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Q4</td>
          <td>634.50</td>
          <td>612.94</td>
          <td>9.55</td>
          <td>302690</td>
          <td class="good">30</td>
          <td>Lower paging and shorter runtime in this run.</td>
        </tr>
        <tr>
          <td>Q8</td>
          <td>640.34</td>
          <td>577.07</td>
          <td>8.24</td>
          <td>430204</td>
          <td class="warn">100</td>
          <td>More pageins/pageouts; consistent with higher unified memory usage.</td>
        </tr>
      </tbody>
    </table>

    <h3>Delta Summary (Q8 relative to Q4)</h3>
    <ul>
      <li><strong>Generation speed:</strong> Q8 is ~38% slower (16.4 vs 26.6 t/s).</li>
      <li><strong>Run duration:</strong> Q8 is ~57% longer (24.03s vs 15.26s).</li>
      <li><strong>Metal model memory:</strong> Q8 uses +3452 MiB more for model weights (8137 - 4685).</li>
      <li><strong>Metal used total:</strong> Q8 uses +3453 MiB more (8908 - 5455).</li>
      <li><strong>Paging:</strong> Q8 ended with higher pageouts (100 vs 30) and pageins (430204 vs 302690).</li>
    </ul>
  </section>

  <section>
    <h2>5) Important Interpretation Notes</h2>
    <h3>Why RSS (~600 MB) does not match the 5–9 GB model footprint</h3>
    <ul>
      <li><strong>RSS</strong> is “resident memory attributed to the process” by the OS accounting. It mainly reflects CPU-side resident pages.</li>
      <li>With Metal on Apple Silicon, a large portion of allocations are in <strong>unified/GPU-managed memory</strong>, which does not necessarily appear as RSS in a 1:1 way.</li>
      <li>For model footprint, <strong>use llama.cpp’s Metal memory breakdown</strong> (model/context/compute) as the primary signal.</li>
      <li>Use RSS mostly for <strong>phase timing</strong> (load ramp vs steady-state) and for detecting unusual process-level changes.</li>
    </ul>

    <h3>Why macOS “Memory Used” can drop after repeated runs</h3>
    <ul>
      <li>macOS actively rebalances memory by compressing, purging caches, and throttling background apps.</li>
      <li>Repeated large allocations can cause the OS to reclaim memory from other processes, making “Memory Used” appear lower later.</li>
      <li>This is why multi-trial runs (median reporting) are needed for stable comparisons.</li>
    </ul>
  </section>

  <section>
    <h2>6) Next Steps (Milestone 3)</h2>
    <ul>
      <li>Run both quantizations across multiple ctx values (e.g., 2048 / 4096 / 8192).</li>
      <li>Plot: <strong>generation TPS vs ctx</strong>, and <strong>Metal context memory vs ctx</strong>.</li>
      <li>Identify the practical ctx ceiling before pageouts and throughput collapse.</li>
      <li>Run multiple trials per config and report medians + variability.</li>
    </ul>
  </section>

  <section>
    <h2>7) Reproduce</h2>
    <pre><code>./src/run_os.sh models/llama3.1-8b-instruct-q4_k_m.gguf 4096 256 q4_capture
./src/run_os.sh models/llama3.1-8b-instruct-q8_0.gguf   4096 256 q8_capture</code></pre>
  </section>

</body>
</html>




# ts = timestamp
# rss_mb = resident set size in MB CPU visible Footprint
# cpu_pct = CPU usage percentage
# mem_pressure_level = memory pressure levels (0=normal, 1=warning, 2=critical)
# pageins_delta = number of pages read from disk to RAM since run start
# pageouts_delta = number of pages written from RAM to disk since run startd


# the run launched the scripit and the script spaws the llama-cli, which is the child process that launches the weights , lkv cache and inference related work

# When passing hte sprit pid into the sample_os for extracting the metrics, the rss and cpu are for the cript not for the llama-cli


# we need to get the global metrcis for system wide pressure

# per process metrics tracking only the llama cli