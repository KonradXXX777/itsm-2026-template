#!/usr/bin/env bash
# ai-generated: 100% - Codex provided isolated replay of an untouched archive; stop preserves the extracted working copy.
set -euo pipefail
lab4_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lab4_container=itsm-lab4-replay
lab4_label=lab4-rec-1
lab4_action="${1:-start}"
if docker container inspect "$lab4_container" >/dev/null 2>&1; then
  if [[ "$(docker inspect --format '{{index .Config.Labels "itsm.lab4.recording"}}' "$lab4_container")" != "$lab4_label" ]]; then
    echo "Refusing to operate on a container without this script's recording label." >&2
    exit 1
  fi
  case "$lab4_action" in
    start) docker start "$lab4_container" ;;
    stop) docker stop "$lab4_container"; exit 0 ;;
    *) echo "Usage: bash scripts/lab4_replay.sh [start|stop]" >&2; exit 2 ;;
  esac
elif [[ "$lab4_action" == start ]]; then
  lab4_data="$(mktemp -d /tmp/itsm-lab4-replay.XXXXXX)"
  tar -xzf "$lab4_root/incident/tsdb-snapshot.tar.gz" -C "$lab4_data"
  docker run --detach --name "$lab4_container" \
    --label "itsm.lab4.recording=$lab4_label" \
    --user "$(id -u):$(id -g)" \
    --publish 127.0.0.1:19091:9090 \
    --volume "$lab4_data:/prometheus" \
    --volume "$lab4_root/prometheus/recording.yml:/etc/prometheus/prometheus.yml:ro" \
    prom/prometheus:v3.15.0 \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/prometheus --storage.tsdb.retention.time=100y
elif [[ "$lab4_action" == stop ]]; then
  echo "Replay container does not exist; nothing to stop."
  exit 0
else
  echo "Usage: bash scripts/lab4_replay.sh [start|stop]" >&2
  exit 2
fi
echo "Historical Prometheus: http://127.0.0.1:19091 (select 2026-10-12 04:56Z or 05:06Z, not now)."
echo "The original archive is unchanged. Stop with: bash scripts/lab4_replay.sh stop"
