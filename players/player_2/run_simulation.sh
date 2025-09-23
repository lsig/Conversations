# Input arguments
length=$1
subjects=$2
memory_size=$3
players_num=$4
sim_num=$5
tmp_json_file=$6
csv_file=$7

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

# Write CSV header once
echo "length,subjects,memory_size,seed,total_players,total,shared,individual,rankings" > $csv_file

for ((i=1; i<=sim_num; i++)); do
    echo "Simulation $i"
    # Run simulation
    touch $tmp_json_file
    $PYEXE $PYFLAGS main.py --player p2 1 --player pr 2 --length $length --subjects $subjects --memory_size $memory_size  --seed $i > $tmp_json_file

    # Process JSON
    $PYEXE $PYFLAGS players/player_2/process_json.py \
        --file $tmp_json_file \
        --length $length \
        --subjects $subjects \
        --memory_size $memory_size \
        --seed $i \
        --players $players_num >> $csv_file
#     uv run python main.py --player p2 1 --player pr 2 --length $length --subjects $subjects --memory_size $memory_size  --seed $i > $tmp_json_file

#     # Delete first two line
#     sed -i '' '1,2d' $tmp_json_file

#     # Process JSON
#     echo "total,shared,individual" >> $csv_file
#     python players/player_2/process_json.py --file $tmp_json_file --length $length --players $players_num >> $csv_file
done
