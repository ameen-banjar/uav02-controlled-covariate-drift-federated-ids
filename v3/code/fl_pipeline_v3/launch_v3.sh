#!/bin/sh
# UAV-02 v3 campaign: every frozen job, at most 3 in parallel, low priority; resumes (completed jobs are skipped).
cd "$(dirname "$0")"
mkdir -p logs_v3
python3.11 -B run_v3.py --list-jobs > logs_v3/_jobs.txt
cat > logs_v3/_one.sh <<'EOS'
#!/bin/sh
cd "$(dirname "$0")/.."
f="logs_v3/$(echo "$1" | tr '|' '_').log"
nice -n 15 python3.11 -B run_v3.py --job "$1" >> "$f" 2>&1
echo "$1 exit $?" >> logs_v3/_done.txt
EOS
chmod +x logs_v3/_one.sh
xargs -P 3 -I{} logs_v3/_one.sh "{}" < logs_v3/_jobs.txt
echo ALL_DONE >> logs_v3/_done.txt
