#!/usr/bin/env bash
set -euo pipefail

# path to the modle
MODEL="${1:?usage: run_one.sh <model.gguf> <ctx> <gen_tokens> <tag>}"
# context size
CTX="${2:?usage: run_one.sh <model.gguf> <ctx> <gen_tokens> <tag>}"
# number of tokens to generate
GEN="${3:?usage: run_one.sh <model.gguf> <ctx> <gen_tokens> <tag>}"
# tag for the run like q4 or q8
TAG="${4:?usage: run_one.sh <model.gguf> <ctx> <gen_tokens> <tag>}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN_ID="$(date +%Y-%m-%dT%H-%M-%S)_${TAG}_ctx${CTX}"
OUTDIR="$ROOT/runs/$RUN_ID"
mkdir -p "$OUTDIR"

PROMPT_FILE="$ROOT/prompts/short.txt"
LLAMA_BIN="$ROOT/../llama.cpp/build/bin/llama-cli"

# Save config
cat > "$OUTDIR/config.txt" << CFG
model=$MODEL
ctx=$CTX
gen_tokens=$GEN
prompt=$PROMPT_FILE
tag=$TAG
CFG

# Start llama in background (non-interactive)
PROMPT_TEXT="$(cat "$PROMPT_FILE")"

script -q "$OUTDIR/llama_output.log" \
"$LLAMA_BIN" \
-m "$MODEL" \
--single-turn \
--prompt "$PROMPT_TEXT" \
-c "$CTX" \
-n "$GEN" \
--no-display-prompt \
--show-timings \
--perf \
</dev/null >/dev/null 2>&1 &

SCRIPT_PID=$!
echo "$SCRIPT_PID" > "$OUTDIR/script_pid.txt"

# Wait briefly for script to spawn llama-cli
sleep 0.2

LLAMA_PID="$(pgrep -P "$SCRIPT_PID" | head -n 1 || true)"
if [[ -z "${LLAMA_PID:-}" ]]; then
  echo "ERROR: could not find llama-cli child PID (parent script PID=$SCRIPT_PID)" >&2
  exit 1
fi

echo "$LLAMA_PID" > "$OUTDIR/llama_pid.txt"

# Start telemetry sampler on the real llama process
"$ROOT/src/sample_os.sh" "$LLAMA_PID" "$OUTDIR/metrics.csv" 0.5 &
SAMP_PID=$!

# Wait for llama to finish, then stop sampler
wait "$SCRIPT_PID" || true
kill "$SAMP_PID" 2>/dev/null || true

echo "Run complete: $OUTDIR"



