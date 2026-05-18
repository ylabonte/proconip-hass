#!/usr/bin/env bash
# Start the ProCon.IP mock in the background, then verify it actually
# responds before returning. Without this readiness check, a silent
# failure (port already in use, missing dependency, import error) would
# leave the devcontainer "green" with no running mock — and developers
# would only discover that when their first request to :8080 hangs.
#
# Invoked by .devcontainer/devcontainer.json's `postStartCommand` and
# safe to run manually inside the container.

set -euo pipefail

# Default mirrors the mock's own default in __main__.py (loopback-only).
# `.devcontainer/devcontainer.json` overrides this to 0.0.0.0 so the forwarded
# port works from outside the container.
export PROCONIP_MOCK_HOST="${PROCONIP_MOCK_HOST:-127.0.0.1}"
PORT="${PROCONIP_MOCK_PORT:-8080}"
USER="${PROCONIP_MOCK_USER:-admin}"
PASS="${PROCONIP_MOCK_PASS:-admin}"
LOG="/tmp/proconip-mock.log"
READY_TIMEOUT_S=15
PYTHON="${PYTHON:-python}"

nohup "$PYTHON" -m tools.proconip_mock > "$LOG" 2>&1 &
PID=$!

# Poll the health-equivalent endpoint until it answers or we run out of time.
for _ in $(seq 1 "$READY_TIMEOUT_S"); do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "ERROR: ProCon.IP mock exited during startup. Tail of $LOG:" >&2
    tail -n 20 "$LOG" >&2 || true
    exit 1
  fi
  if curl --silent --fail --max-time 1 -u "$USER:$PASS" \
        "http://localhost:$PORT/GetState.csv" >/dev/null; then
    echo "ProCon.IP mock ready on http://$PROCONIP_MOCK_HOST:$PORT (pid=$PID, log=$LOG)"
    exit 0
  fi
  sleep 1
done

echo "WARNING: ProCon.IP mock did not respond on :$PORT within ${READY_TIMEOUT_S}s." >&2
echo "Tail of $LOG:" >&2
tail -n 20 "$LOG" >&2 || true
# Exit non-zero so the container surface treats this as a failed postStart.
exit 1
