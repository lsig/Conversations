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
touch $tmp_json_file

# Detect Python 3 interpreter (Linux/macOS/Windows Python Launcher)
PYEXE=""
PYFLAGS=""
if command -v python3 >/dev/null 2>&1; then
    PYEXE="python3"
elif command -v python >/dev/null 2>&1; then
    PYEXE="python"
elif command -v py >/dev/null 2>&1; then
    PYEXE="py"
    PYFLAGS="-3"
else
    echo "Error: Python 3 not found on PATH" >&2
    exit 1
fi

for ((i=1; i<=sim_num; i++)); do
    # Randomize parameters
    # length=$((20 + RANDOM % 381))        # random length between 20 and 400
    # subjects=$((5 + RANDOM % 46))        # random subjects between 5 and 50
    # memory_size=$((5 + RANDOM % 16))     # random memory_size between 5 and 20
    # seed=$((RANDOM * RANDOM))            # random seed

    length=100
    subjects=10
    memory_size=15
    seed=$((RANDOM * RANDOM))
    max_players=10
    player_types=(p1 p2 p3 p4 p5 p6 p7 p8 p9 p10)
    random_player=true

    # Always at least 1 (up to 4) Player2s, random 0-2 for p1, p3-p10, cap at 13
    player_args=""
    total_players=1
    # Players
    p1_count=0
    p2_count=1 #$((1 + RANDOM % 4))
    p3_count=0
    p4_count=0
    p5_count=0
    p6_count=0
    p7_count=0
    p8_count=0
    p9_count=0
    p10_count=0
    pr_count=0
    prp_count=0
    pp_count=0

    # Loop to add all other players and if random_player is true then also add random players
    if [ $random_player ]; then
        player_types=(p1 p2 p3 p4 p5 p6 p7 p8 p9 p10 pr prp pp)
    fi
    while [ $total_players -lt $max_players ]; do
        idx=$((RANDOM % ${#player_types[@]}))
        type=${player_types[$idx]}
        # Add 1 player to its counter
        case $type in
            p1) if [ $p1_count -lt 2 ]; then p1_count=$((p1_count + 1)); total_players=$((total_players + 1)); fi ;;
            p2) if [ $p2_count -lt 4 ]; then p2_count=$((p2_count + 1)); total_players=$((total_players + 1)); fi ;;
            p3) if [ $p3_count -lt 2 ]; then p3_count=$((p3_count + 1)); total_players=$((total_players + 1)); fi ;;
            p4) if [ $p4_count -lt 2 ]; then p4_count=$((p4_count + 1)); total_players=$((total_players + 1)); fi ;;
            p5) if [ $p5_count -lt 2 ]; then p5_count=$((p5_count + 1)); total_players=$((total_players + 1)); fi ;;
            p6) if [ $p6_count -lt 2 ]; then p6_count=$((p6_count + 1)); total_players=$((total_players + 1)); fi ;;
            p7) if [ $p7_count -lt 2 ]; then p7_count=$((p7_count + 1)); total_players=$((total_players + 1)); fi ;;
            p8) if [ $p8_count -lt 2 ]; then p8_count=$((p8_count + 1)); total_players=$((total_players + 1)); fi ;;
            p9) if [ $p9_count -lt 2 ]; then p9_count=$((p9_count + 1)); total_players=$((total_players + 1)); fi ;;
            p10) if [ $p10_count -lt 2 ]; then p10_count=$((p10_count + 1)); total_players=$((total_players + 1)); fi ;;
            pr) if [ $pr_count -lt 2 ]; then pr_count=$((pr_count + 1)); total_players=$((total_players + 1)); fi ;;
            prp) if [ $prp_count -lt 2 ]; then prp_count=$((prp_count + 1)); total_players=$((total_players + 1)); fi ;;
            pp) if [ $pp_count -lt 2 ]; then pp_count=$((pp_count + 1)); total_players=$((total_players + 1)); fi ;;
        esac
    done
    # Construct player_args
    if [ $p1_count -gt 0 ]; then
        player_args="$player_args --player p1 $p1_count"
    fi
    if [ $p2_count -gt 0 ]; then
        player_args="$player_args --player p2 $p2_count"
    fi
    if [ $p3_count -gt 0 ]; then
        player_args="$player_args --player p3 $p3_count"
    fi
    if [ $p4_count -gt 0 ]; then
        player_args="$player_args --player p4 $p4_count"
    fi
    if [ $p5_count -gt 0 ]; then
        player_args="$player_args --player p5 $p5_count"
    fi
    if [ $p6_count -gt 0 ]; then
        player_args="$player_args --player p6 $p6_count"
    fi
    if [ $p7_count -gt 0 ]; then
        player_args="$player_args --player p7 $p7_count"
    fi
    if [ $p8_count -gt 0 ]; then
        player_args="$player_args --player p8 $p8_count"
    fi
    if [ $p9_count -gt 0 ]; then
        player_args="$player_args --player p9 $p9_count"
    fi
    if [ $p10_count -gt 0 ]; then
        player_args="$player_args --player p10 $p10_count"
    fi
    if [ $pr_count -gt 0 ]; then
        player_args="$player_args --player pr $pr_count"
    fi
    if [ $prp_count -gt 0 ]; then
        player_args="$player_args --player prp $prp_count"
    fi
    if [ $pp_count -gt 0 ]; then
        player_args="$player_args --player pp $pp_count"
    fi


    # Other players
    # for pid in 1 3 4 5 6 7 8 9 10; do
    #     if [ $total_players -ge $max_players ]; then
    #         break
    #     fi
    #     count=$((RANDOM % 3))  # random count between 0 and 2
    #     if [ $((total_players + count)) -gt $max_players ]; then
    #         count=$((max_players - total_players))
    #     fi
    #     total_players=$((total_players + count))
    #     if [ $count -gt 0 ]; then
    #         player_args="$player_args --player p$pid $count"
    #     fi
    # done
    # for rtype in pr prp pp; do
    #     if [ $total_players -ge $max_players ]; then
    #         break
    #     fi
    #     rcount=$((RANDOM % 2))
    #     if [ $((total_players + rcount)) -gt $max_players ]; then
    #         rcount=$((max_players - total_players))
    #     fi
    #     total_players=$((total_players + rcount))
    #     if [ $rcount -gt 0 ]; then
    #         player_args="$player_args --player $rtype $rcount"
    #     fi
    # done

    echo "Simulation $i: length=$length, subjects=$subjects, memory_size=$memory_size, seed=$seed, total_players=$total_players"
    #echo which players are included
    echo "Players: p1:$p1_count p2:$p2_count p3:$p3_count p4:$p4_count p5:$p5_count p6:$p6_count p7:$p7_count p8:$p8_count p9:$p9_count p10:$p10_count pr:$pr_count prp:$prp_count pp:$pp_count"
    
    touch $tmp_json_file
    $PYEXE $PYFLAGS main.py $player_args --length $length --subjects $subjects --memory_size $memory_size --seed $seed | tail -n +3 > $tmp_json_file


    # Process JSON
    if [ $i -eq 1 ]; then
        echo "length,subjects,memory_size,seed,total_players,total,shared,individual,rankings" > $csv_file
    fi
    $PYEXE $PYFLAGS players/player_2/process_json.py \
        --file $tmp_json_file \
        --length $length \
        --subjects $subjects \
        --memory_size $memory_size \
        --seed $seed \
        --players $total_players >> $csv_file

done
