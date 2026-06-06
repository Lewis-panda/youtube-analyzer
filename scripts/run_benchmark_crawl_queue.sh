#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/lewis/NTU_Course/SMA/Youtube-Network/ChannelCommunityAnalyzer"
INGEST_ROOT="/home/lewis/NTU_Course/SMA/Youtube-Network/youtube_graph_ingest"
QUEUE_TOOL="$ROOT/scripts/benchmark_queue.py"

SEED_FILE="${SEED_FILE:-$ROOT/docs/tw_benchmark_verified_full_channel_urls.txt}"
PUBLISHED_AFTER="${PUBLISHED_AFTER:-2023-01-01}"
BATCH_LIMIT="${BATCH_LIMIT:-50}"
MAX_BATCHES="${MAX_BATCHES:-200}"
SLEEP_SECONDS="${SLEEP_SECONDS:-10}"
SKIP_SEED="${SKIP_SEED:-0}"
RESET_STALE_RESOLVING="${RESET_STALE_RESOLVING:-0}"

cd "$INGEST_ROOT"

echo "== benchmark crawl started at $(date -Is) =="
echo "seed_file=$SEED_FILE"
echo "published_after=$PUBLISHED_AFTER"
echo "batch_limit=$BATCH_LIMIT"
echo "max_batches=$MAX_BATCHES"
echo "skip_seed=$SKIP_SEED"
echo "reset_stale_resolving=$RESET_STALE_RESOLVING"
echo

if [ "$RESET_STALE_RESOLVING" = "1" ]; then
  echo "== reset stale resolving rows =="
  python3 "$QUEUE_TOOL" reset-stale-resolving --older-than-minutes 30
fi

if [ "$SKIP_SEED" = "1" ]; then
  echo "== seed skipped =="
else
  echo "== seed =="
  micromamba run -n llm-opt python -u -m yt_graph.cli seed \
    --file "$SEED_FILE" \
    --published-after "$PUBLISHED_AFTER"
fi

echo
echo "== initial status =="
micromamba run -n llm-opt python -u -m yt_graph.cli status
python3 "$QUEUE_TOOL" status --limit 5

for batch in $(seq 1 "$MAX_BATCHES"); do
  echo
  echo "== crawl batch $batch at $(date -Is) =="
  no_more_queue=0
  for item in $(seq 1 "$BATCH_LIMIT"); do
    echo "-- crawl item $item/$BATCH_LIMIT at $(date -Is) --"
    item_tmp="$(mktemp)"
    set +e
    micromamba run -n llm-opt python -u -m yt_graph.cli crawl-next \
      --published-after "$PUBLISHED_AFTER" 2>&1 | tee "$item_tmp"
    crawl_status=${PIPESTATUS[0]}
    set -e

    if grep -q "quotaExceeded" "$item_tmp"; then
      echo "quotaExceeded detected; resetting quota failures and pausing."
      python3 "$QUEUE_TOOL" reset-quota
      rm -f "$item_tmp"

      echo
      echo "== build-all before quota pause at $(date -Is) =="
      micromamba run -n llm-opt python -u -m yt_graph.cli build-all

      echo
      echo "== status at quota pause =="
      micromamba run -n llm-opt python -u -m yt_graph.cli status
      python3 "$QUEUE_TOOL" status --limit 5

      echo "benchmark crawl paused at $(date -Is)"
      exit 75
    fi

    if [ "$crawl_status" -ne 0 ]; then
      echo "crawl-next failed with status $crawl_status; continuing because the queue item was marked failed."
      rm -f "$item_tmp"
      continue
    fi

    if grep -q "No queued URL." "$item_tmp"; then
      no_more_queue=1
      rm -f "$item_tmp"
      break
    fi
    rm -f "$item_tmp"
  done

  echo
  echo "== build-all after batch $batch at $(date -Is) =="
  micromamba run -n llm-opt python -u -m yt_graph.cli build-all

  echo
echo "== status after batch $batch =="
  micromamba run -n llm-opt python -u -m yt_graph.cli status
  python3 "$QUEUE_TOOL" status --limit 5

  if [ "$no_more_queue" = "1" ]; then
    echo "queue is empty; benchmark crawl finished at $(date -Is)"
    exit 0
  fi

  sleep "$SLEEP_SECONDS"
done

echo "reached MAX_BATCHES=$MAX_BATCHES at $(date -Is)"
