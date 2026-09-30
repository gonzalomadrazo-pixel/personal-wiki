#!/usr/bin/env bash
# Full offline demonstration (about 4 minutes).
# Before running: quit every app except Terminal (including Claude and menu-bar apps), make sure
# Ollama is open, start a screen recording, and turn Wi-Fi OFF. Then run:  scripts/offline_demo.sh
# Everything is logged to evidence/offline/.
set -u
cd "$(dirname "$0")/.."
STAMP=$(date +%Y%m%d-%H%M%S)
OUT=evidence/offline/offline-demo-$STAMP.txt
export NO_COLOR=1
{
  echo "=== Offline demo $STAMP"
  echo "\$ networksetup -getairportpower en0"; networksetup -getairportpower en0 2>/dev/null || true
  echo "\$ curl -sS -m 5 https://www.google.com -o /dev/null"; curl -sS -m 5 https://www.google.com -o /dev/null && echo "INTERNET REACHABLE" || echo "(no internet, as expected)"
  echo; echo "\$ ollama list   # weights are stored locally"; ollama list
  echo; echo "\$ ./wiki status --check-network"; ./wiki status --check-network
  echo; echo "\$ ./wiki --help"; ./wiki --help
  echo; echo "\$ ./wiki ingest vault/raw/rochon-2002-giverny-letter.md --force   # re-run Gemma on one source"
  ./wiki ingest vault/raw/rochon-2002-giverny-letter.md --force
  echo; echo "\$ ./wiki ingest vault/raw   # re-ingest all: must reuse extractions, no duplicate pages"
  ./wiki ingest vault/raw
  echo; echo "\$ find vault/wiki -name '*.md' | sort"; find vault/wiki -name '*.md' | sort
  echo; echo "\$ ./wiki eval   # the four ask-mode tests"; ./wiki eval
  echo; echo "\$ ./wiki status   # memory after the runs"; ./wiki status
  echo; echo "\$ sysctl vm.swapusage"; sysctl vm.swapusage
} 2>&1 | tee "$OUT"
scripts/mode_checks.sh
echo "Saved offline transcript → $OUT"
