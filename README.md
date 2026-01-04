<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OsTelemetry – llama.cpp Quantization QoS Study</title>

  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      line-height: 1.5;
      margin: 28px;
      max-width: 1080px;
    }

    h1, h2, h3 {
      margin-top: 28px;
      margin-bottom: 12px;
    }

    p {
      margin: 8px 0 14px 0;
    }

    ul {
      margin: 6px 0 14px 22px;
    }

    li {
      margin: 6px 0;
    }

    code, pre {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    pre {
      background: #f6f8fa;
      padding: 14px;
      border-radius: 8px;
      overflow-x: auto;
      margin: 12px 0;
    }

    table {
      border-collapse: collapse;
      width: 100%;
      margin: 14px 0 20px 0;
    }

    th, td {
      border: 1px solid #ddd;
      padding: 10px;
      vertical-align: top;
    }

    th {
      background: #f3f4f6;
      text-align: left;
    }

    .muted {
      color: #555;
    }

    .good {
      font-weight: 600;
    }

    .warn {
      font-weight: 600;
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .card {
      border: 1px solid #ddd;
      border-radius: 10px;
      padding: 16px;
    }

    .tiny {
      font-size: 0.9em;
      line-height: 1.4;
      color: #555;
    }

    footer {
      margin-top: 36px;
      padding-top: 14px;
      border-top: 1px solid #ddd;
    }
  </style>
</head>

<body>

  <header>
    <h1>OsTelemetry: llama.cpp Quantization QoS Study</h1>
    <p class="muted">
      Personal study focused on performance and memory tradeoffs between quantized GGUF models
      (Q4 vs Q8) running on macOS with Apple Silicon and Metal acceleration.
    </p>
  </header>

  <section>
    <h2>1. Overview</h2>
    <p>
      This project explores inference QoS characteristics for quantized large language models
      using <code>llama.cpp</code> on macOS. The focus is on practical system behavior rather than
      theoretical benchmarks.
    </p>
    <ul>
      <li>Whether a model fits in unified memory at a given context length (<code>ctx</code>)</li>
      <li>Token generation throughput (tokens/sec)</li>
      <li>System-level paging and memory pressure during repeated runs</li>
    </ul>
  </section>

  <section>
    <h2>2. What Is Tracked</h2>

    <h3>Per-run artifacts</h3>
    <ul>
      <li><code>llama_output.log</code> – model output, <code>--perf</code> stats, Metal memory breakdown</li>
      <li><code>metrics.csv</code> – sampled OS telemetry (RSS, CPU, paging, VM pressure)</li>
      <li><code>config.txt</code> – model path, context size, generation tokens, run tag</li>
    </ul>

    <h3>OS telemetry fields (<code>metrics.csv</code>)</h3>
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>Description</th>
          <th>Usage</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>ts</code></td>
          <td>Timestamp (seconds since epoch)</td>
          <td>Align load, generation, and teardown phases</td>
        </tr>
        <tr>
          <td><code>rss_mb</code></td>
          <td>Resident memory attributed to sampled PID</td>
          <td>Phase-level trends only</td>
        </tr>
        <tr>
          <td><code>cpu_pct</code></td>
          <td>CPU utilization (%)</td>
          <td>CPU-side workload alongside Metal compute</td>
        </tr>
        <tr>
          <td><code>vm_pressure_flag</code></td>
          <td>VM pressure level (1 normal, 2 warning, 4 critical)</td>
          <td>System-wide memory stress indicator</td>
        </tr>
        <tr>
          <td><code>avail_mem_level</code></td>
          <td>macOS memory availability scalar</td>
          <td>Tracks OS reclaim/compression behavior</td>
        </tr>
        <tr>
          <td><code>pageins_delta</code></td>
          <td>Pages loaded from disk → RAM</td>
          <td>Detects faulting under pressure</td>
        </tr>
        <tr>
          <td><code>pageouts_delta</code></td>
          <td>Pages evicted from RAM → disk</td>
          <td>Detects eviction activity</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>3. Current Progress</h2>
    <div class="grid">
      <div class="card">
        <h3>Harness & Telemetry</h3>
        <ul>
          <li>Automated, non-interactive runs</li>
          <li>OS telemetry sampling for memory and CPU</li>
          <li>Stable single-turn inference capture</li>
        </ul>
      </div>
      <div class="card">
        <h3>Q4 vs Q8 Comparison</h3>
        <ul>
          <li>Parsed throughput from <code>--perf</code></li>
          <li>Extracted Metal memory breakdown</li>
          <li>Summarized runtime, paging, and CPU usage</li>
        </ul>
      </div>
    </div>
  </section>

  <section>
    <h2>4. Latest Comparison</h2>
    <p class="muted">
      Context = 4096 · Generation tokens = 256
    </p>

    <h3>Throughput & runtime</h3>
    <table>
      <thead>
        <tr>
          <th>Model</th>
          <th>Prompt TPS</th>
          <th>Generation TPS</th>
          <th>Duration (s)</th>
          <th>Notes</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Q4 (Q4_K_M)</td>
          <td>16312.7</td>
          <td class="good">26.6</td>
          <td class="good">15.26</td>
          <td>Faster generation and shorter runtime</td>
        </tr>
        <tr>
          <td>Q8 (Q8_0)</td>
          <td>15393.6</td>
          <td>16.4</td>
          <td>24.03</td>
          <td>Slower generation under same settings</td>
        </tr>
      </tbody>
    </table>

    <h3>Metal / host memory breakdown</h3>
    <table>
      <thead>
        <tr>
          <th>Model</th>
          <th>Metal Used (MiB)</th>
          <th>Model (MiB)</th>
          <th>Context (MiB)</th>
          <th>Compute (MiB)</th>
          <th>Host (MiB)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Q4</td>
          <td>5455</td>
          <td class="good">4685</td>
          <td>512</td>
          <td>258</td>
          <td>297</td>
        </tr>
        <tr>
          <td>Q8</td>
          <td class="warn">8908</td>
          <td class="warn">8137</td>
          <td>512</td>
          <td>258</td>
          <td>548</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>5. Interpretation Notes</h2>

    <h3>RSS vs actual model footprint</h3>
    <ul>
      <li>RSS reflects CPU-visible resident pages only</li>
      <li>Metal allocations live in GPU-managed unified memory</li>
      <li>Use llama.cpp Metal breakdown for capacity planning</li>
      <li>Use RSS mainly for phase detection</li>
    </ul>

    <h3>Why macOS memory usage shifts across runs</h3>
    <ul>
      <li>macOS aggressively compresses and reclaims memory</li>
      <li>Large allocations trigger cache purging</li>
      <li>Single runs are noisy; trends matter more</li>
    </ul>
  </section>

  <section>
    <h2>6. Reproduce</h2>
    <pre><code>./src/run_os.sh models/llama3.1-8b-instruct-q4_k_m.gguf 4096 256 q4_capture
./src/run_os.sh models/llama3.1-8b-instruct-q8_0.gguf   4096 256 q8_capture</code></pre>
  </section>

  <footer>
    <div class="tiny">
      <p><strong>Abbreviations & notes</strong></p>
      <ul>
        <li><code>rss_mb</code>: CPU-visible resident memory (not full Metal usage)</li>
        <li><code>cpu_pct</code>: CPU utilization of sampled PID</li>
        <li><code>mem_pressure_level</code>: 0 normal · 1 warning · 2 critical</li>
        <li><code>pageins_delta</code>: Pages loaded from disk → RAM</li>
        <li><code>pageouts_delta</code>: Pages evicted from RAM → disk</li>
      </ul>
      <p>
        The benchmark script launches <code>llama-cli</code> as a child process.
        If OS sampling targets the wrapper script PID, RSS and CPU metrics reflect
        the wrapper rather than the inference process itself. System-wide pressure
        metrics are therefore required for accurate interpretation.
      </p>
    </div>
  </footer>

</body>
</html>