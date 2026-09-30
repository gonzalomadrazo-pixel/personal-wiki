#!/usr/bin/env bash
# Chat / search / ask boundary checks. Output is saved to evidence/mode-checks/.
set -u
cd "$(dirname "$0")/.."
OUT=evidence/mode-checks/transcript-$(date +%Y%m%d-%H%M%S).txt
export NO_COLOR=1
{
  echo "=== $(date) · network: $(./wiki status --check-network | grep Network)"
  echo; echo "\$ ./wiki chat --script evals/chat_checks.txt"
  ./wiki chat --script evals/chat_checks.txt
  echo; echo "\$ ./wiki search \"Mr. Market\" -k 3"
  ./wiki search "Mr. Market" -k 3
  echo; echo "\$ ./wiki ask \"According to Howard Marks, when is the best time to buy stocks?\""
  ./wiki ask "According to Howard Marks, when is the best time to buy stocks?"
} 2>&1 | tee "$OUT"
echo "Saved transcript → $OUT"
