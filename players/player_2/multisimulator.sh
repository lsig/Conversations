#!/bin/bash
# Randomized simulation runner

#Example usage:
# ./run_simulation_random.sh 10 results.csv
# Input arguments:
# 1. Number of simulations (sim_num)
# 2. Output CSV file (csv_file)

sim_num=$1
csv_file=$2

tmp_json_file="tmp.json"

for ((i=1; i<=sim_num; i++)); do
    # Randomize parameters
    length=$((20 + RANDOM % 381))         # random length between 20 and 400
    subjects=$((5 + RANDOM % 46))        # random subjects between 5 and 50
    memory_size=$((5 + RANDOM % 16))     # random memory_size between 5 and 20
    seed=$((RANDOM * RANDOM))            # random seed

    # Randomize player counts for p1-p10 and random types
    player_args=""
    total_players=0
    for pid in {1..10}; do
        count=$((RANDOM % 4))
        total_players=$((total_players + count))
        if [ $count -gt 0 ]; then
            player_args="$player_args --player p$pid $count"
        fi
    done
    for rtype in pr prp pp; do
        rcount=$((RANDOM % 4))
        total_players=$((total_players + rcount))
        if [ $rcount -gt 0 ]; then
            player_args="$player_args --player $rtype $rcount"
        fi
    done

    echo "Simulation $i: length=$length, subjects=$subjects, memory_size=$memory_size, seed=$seed, total_players=$total_players"
    touch $tmp_json_file
    uv run python main.py $player_args --length $length --subjects $subjects --memory_size $memory_size --seed $seed > $tmp_json_file

    # Remove first two lines if present (Linux/WSL compatible)
    sed -i '1,2d' $tmp_json_file

    # Process JSON
    if [ $i -eq 1 ]; then
        echo "total,shared,individual" > $csv_file
    fi
    python players/player_2/process_json.py --file $tmp_json_file --length $length --players $total_players >> $csv_file

done
