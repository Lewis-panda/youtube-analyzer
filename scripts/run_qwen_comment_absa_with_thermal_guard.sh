#!/usr/bin/env bash
set -u

if [[ $# -lt 9 ]]; then
  cat >&2 <<'USAGE'
Usage: scripts/run_qwen_comment_absa_with_thermal_guard.sh HOURS LOG_PATH TEMP_LIMIT_C CHECK_INTERVAL_SECONDS COOLDOWN_SECONDS CONFIG OUTPUT SCOPE INCLUDE_REPLIES_FLAG [EXTRA_ARGS...]

Runs Qwen comment ABSA with a GPU temperature guard. If the GPU reaches
TEMP_LIMIT_C, the running process is interrupted, the script waits
COOLDOWN_SECONDS, then retries the same ABSA command. Existing output rows are
reused by scripts/run_qwen_comment_absa.py, so retrying resumes by unit_id.

INCLUDE_REPLIES_FLAG must be 0 or 1.
USAGE
  exit 2
fi

hours="$1"
log_path="$2"
temp_limit_c="$3"
check_interval_seconds="$4"
cooldown_seconds="$5"
config_path="$6"
output_path="$7"
scope="$8"
include_replies_flag="$9"
shift 9

deadline_epoch=$(( $(date +%s) + hours * 3600 ))
mkdir -p "$(dirname "$log_path")"

cooling_helper="${QWEN_COOLING_HELPER:-/usr/local/sbin/qwen-cooling-control}"
ACTIVE_CHILD_PID=""

log_msg() {
  printf "%s\n" "$*" | tee -a "$log_path"
}

gpu_temp_c() {
  nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null \
    | awk 'NR==1 {print int($1)}'
}

set_full_cooling() {
  if [[ -x "${cooling_helper}" ]]; then
    sudo -n "${cooling_helper}" full >> "$log_path" 2>&1 \
      && log_msg "cooling: helper set fans to full" \
      || log_msg "cooling: helper failed to set full fans"
  fi
}

restore_auto_cooling() {
  if [[ -x "${cooling_helper}" ]]; then
    sudo -n "${cooling_helper}" auto >> "$log_path" 2>&1 \
      && log_msg "cooling: helper restored fan auto" \
      || log_msg "cooling: helper failed to restore fan auto"
  fi
}

terminate_group() {
  local pid="$1"
  local pgid
  pgid="$(ps -o pgid= -p "$pid" 2>/dev/null | awk '{print $1}')"
  if [[ -n "${pgid}" ]]; then
    kill -INT "-${pgid}" 2>/dev/null || true
    sleep 10
    kill -TERM "-${pgid}" 2>/dev/null || true
  else
    kill -INT "$pid" 2>/dev/null || true
  fi
}

handle_interrupt() {
  log_msg "received interrupt; terminating active ABSA child if present"
  if [[ -n "${ACTIVE_CHILD_PID}" ]] && kill -0 "${ACTIVE_CHILD_PID}" 2>/dev/null; then
    terminate_group "${ACTIVE_CHILD_PID}"
  fi
  exit 130
}

run_absa() {
  local include_args=()
  if [[ "${include_replies_flag}" == "1" ]]; then
    include_args=(--include-replies)
  fi
  setsid micromamba run -n llm-opt python scripts/run_qwen_comment_absa.py \
    --config "${config_path}" \
    --scope "${scope}" \
    --output "${output_path}" \
    "${include_args[@]}" \
    "$@" >> "$log_path" 2>&1 &
  RUN_PID="$!"
  ACTIVE_CHILD_PID="$RUN_PID"
}

log_msg "Qwen comment ABSA thermal guard started $(date -Is)"
log_msg "deadline_epoch=${deadline_epoch}"
log_msg "temp_limit_c=${temp_limit_c}"
log_msg "check_interval_seconds=${check_interval_seconds}"
log_msg "cooldown_seconds=${cooldown_seconds}"
log_msg "config=${config_path}"
log_msg "output=${output_path}"
log_msg "scope=${scope}"
log_msg "include_replies=${include_replies_flag}"
log_msg "extra_args=$*"

trap handle_interrupt INT TERM

if [[ "${QWEN_FULL_COOLING:-1}" == "1" ]]; then
  set_full_cooling
  trap restore_auto_cooling EXIT
fi

while true; do
  now_epoch=$(date +%s)
  if (( now_epoch >= deadline_epoch )); then
    log_msg "deadline reached before completion $(date -Is)"
    exit 0
  fi

  current_temp="$(gpu_temp_c)"
  if [[ -n "${current_temp}" ]]; then
    log_msg "preflight gpu_temp=${current_temp}C $(date -Is)"
    if (( current_temp >= temp_limit_c )); then
      log_msg "preflight temperature over limit; cooling for ${cooldown_seconds}s"
      sleep "$cooldown_seconds"
      continue
    fi
  fi

  log_msg "===== START ABSA $(date -Is) ====="
  RUN_PID=""
  run_absa "$@"
  child_pid="$RUN_PID"
  thermal_pause=0

  while kill -0 "$child_pid" 2>/dev/null; do
    sleep "$check_interval_seconds"
    if ! kill -0 "$child_pid" 2>/dev/null; then
      break
    fi
    current_temp="$(gpu_temp_c)"
    if [[ -z "${current_temp}" ]]; then
      log_msg "thermal check could not read GPU temperature $(date -Is)"
      continue
    fi
    log_msg "thermal check gpu_temp=${current_temp}C limit=${temp_limit_c}C $(date -Is)"
    if (( current_temp >= temp_limit_c )); then
      log_msg "temperature limit reached; interrupting ABSA for cooldown"
      terminate_group "$child_pid"
      thermal_pause=1
      break
    fi
  done

  wait "$child_pid"
  rc=$?
  ACTIVE_CHILD_PID=""
  log_msg "===== END ABSA rc=${rc} $(date -Is) ====="

  if (( thermal_pause == 1 )); then
    log_msg "cooling for ${cooldown_seconds}s before retry"
    sleep "$cooldown_seconds"
    continue
  fi

  exit "$rc"
done
