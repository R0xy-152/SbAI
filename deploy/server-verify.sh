#!/usr/bin/env bash
# 服务器端验收（Linux 无 pwsh 环境用；等价于 deploy/verify.ps1 的基础链路部分）。
# 用法：bash deploy/server-verify.sh [BaseUrl]   （默认 http://127.0.0.1）
set -u
BASE="${1:-http://127.0.0.1}"
PASS=0; FAIL=0
check() {
  name="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "[PASS] $name"; PASS=$((PASS+1));
  else echo "[FAIL] $name"; FAIL=$((FAIL+1)); fi
}
PLAYER="server-check-$$"
check 'health /api/health' curl -fsS -m 15 "$BASE/api/health"
check 'story first node' bash -c "curl -fsS -m 30 -X POST '$BASE/api/story/advance' -H 'Content-Type: application/json' -d '{\"session_id\":null,\"player_id\":\"$PLAYER\"}' | grep -q 'SYSTEM INITIALIZING'"
check 'AUTO save (postgres)' bash -c "curl -fsS -m 15 '$BASE/api/saves?player_id=$PLAYER' | grep -q '\"auto\"'"
check 'static asset deepseek_main.png' curl -fsS -m 20 -o /dev/null "$BASE/char/deepseek/pic/deepseek_main.png"
check 'frontend page /' curl -fsS -m 20 -o /dev/null "$BASE/"
echo "passed=$PASS failed=$FAIL"
test "$FAIL" -eq 0
