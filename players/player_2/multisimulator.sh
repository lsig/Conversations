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

max_players=4  # Set your desired max here
for ((i=1; i<=sim_num; i++)); do
    # Randomize parameters
    # length=$((20 + RANDOM % 381))        # random length between 20 and 400
    # subjects=$((5 + RANDOM % 46))        # random subjects between 5 and 50
    # memory_size=$((5 + RANDOM % 16))     # random memory_size between 5 and 20
    # seed=$((RANDOM * RANDOM))            # random seed

    length=30
    subjects=10
    memory_size=15
    seed=$((RANDOM * RANDOM))

    # Always at least 1 (up to 4) Player2s, random 0-2 for p1, p3-p10, cap at 13
    player_args=""
    total_players=0
    # Player2s
    p2_count=1 #$((1 + RANDOM % 4))
    if [ $p2_count -gt $max_players ]; then
        p2_count=$max_players
    fi
    player_args="$player_args --player p2 $p2_count"
    total_players=$((total_players + p2_count))
    # Other players
    for pid in 1 3 4 5 6 7 8 9 10; do
        if [ $total_players -ge $max_players ]; then
            break
        fi
        count=$((RANDOM % 3))  # random count between 0 and 2
        if [ $((total_players + count)) -gt $max_players ]; then
            count=$((max_players - total_players))
        fi
        total_players=$((total_players + count))
        if [ $count -gt 0 ]; then
            player_args="$player_args --player p$pid $count"
        fi
    done
    for rtype in pr prp pp; do
        if [ $total_players -ge $max_players ]; then
            break
        fi
        rcount=$((RANDOM % 2))
        if [ $((total_players + rcount)) -gt $max_players ]; then
            rcount=$((max_players - total_players))
        fi
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
        echo "length,subjects,memory_size,seed,total_players,total,shared,individual" > $csv_file
    fi
    python players/player_2/process_json.py \
        --file $tmp_json_file \
        --length $length \
        --subjects $subjects \
        --memory_size $memory_size \
        --seed $seed \
        --players $total_players >> $csv_file

done
