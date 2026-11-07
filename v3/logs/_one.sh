#!/bin/sh
cd "$(dirname "$0")/.."
f="logs_v3/$(echo "$1" | tr '|' '_').log"
nice -n 15 python3.11 -B run_v3.py --job "$1" >> "$f" 2>&1
echo "$1 exit $?" >> logs_v3/_done.txt
