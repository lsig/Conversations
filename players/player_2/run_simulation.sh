# Input arguments
length=$1
subjects=$2
memory_size=$3
players_num=$4
sim_num=$5
tmp_json_file=$6
csv_file=$7

for ((i=1; i<=sim_num; i++)); do
    echo "Simulation $i"
    # Run simulation
    touch $tmp_json_file
    uv run python main.py --player p2 1 --player pr 2 --length $length --subjects $subjects --memory_size $memory_size  --seed $i > $tmp_json_file

    # Delete first two line
    sed -i '' '1,2d' $tmp_json_file

    # Process JSON
    echo "total,shared,individual" >> $csv_file
    python players/player_2/process_json.py --file $tmp_json_file --length $length --players $players_num >> $csv_file
done
