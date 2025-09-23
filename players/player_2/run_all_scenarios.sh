#!/bin/bash
# Usage: bash players/player_2/run_all_scenarios.sh
# Adjust MAX_PAR to the number of vCPUs

set -euo pipefail

MAX_PAR=${MAX_PAR:-2}

cat > scenarios.tsv <<'EOF'
length=100 subjects=10 memory=15 players=10
length=100 subjects=20 memory=15 players=10
length=100 subjects=10 memory=25 players=10
length=150 subjects=10 memory=15 players=10
length=30  subjects=10 memory=15 players=6
length=60  subjects=15 memory=15 players=8
length=200 subjects=20 memory=20 players=12
length=120 subjects=12 memory=18 players=10
length=80  subjects=8  memory=12 players=8
length=50  subjects=25 memory=10 players=10
EOF

i=0
running=0
while read -r line; do
  i=$((i+1))
  eval $line
  tmp="tmp_s${i}.json"
  out="results_s${i}.csv"
  bash players/player_2/run_simulation.sh $length $subjects $memory $players 1000 $tmp $out &
  running=$((running+1))
  if [ $running -ge $MAX_PAR ]; then
    wait
    running=0
  fi
done < scenarios.tsv
wait

echo "All scenarios completed. Outputs: results_s*.csv and per-sim JSONs results_s*_sim*.json"
