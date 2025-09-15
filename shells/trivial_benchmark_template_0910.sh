
#          ◅▯◊║◊▯▻   Global Setting   ◅▯◊║◊▯▻

# player to teset
player="p_balanced_greedy"
test_player="p_zipper"

# global setting: (default L 10, B 10, S 20)
L=50  
B=10
S=20

# derived round/output settings
root="results"
round_name="trivial_test_${test_player}"
output_root="$root/${round_name}_L${L}B${B}S${S}"

# test mode control
gui_on="true"  

# Set GUI flag based on gui_on variable
if [ "$gui_on" = "true" ]; then
    gui_flag="--gui"
else
    gui_flag=""
fi

#          ◅▯◊║◊▯▻   Test Case   ◅▯◊║◊▯▻

# # collaboration
python main.py --player $player 10 --length $L --memory_size $B --subjects $S --output_path "$output_root/self_collaboration" --test_player $test_player $gui_flag


# # against random player
python main.py --player $player 2 --player pr 8 --length $L --memory_size $B --subjects $S --output_path "$output_root/against_random_player" --test_player $test_player $gui_flag


# in complex environment 
player_list="p_zipper pr pp p_balanced_greedy p_selfless_greedy p_selfish_greedy"

cmd="python main.py"
player_added=false

for other_player in $player_list; do
    if [ "$other_player" = "$player" ]; then
        cmd="$cmd --player $other_player 4"
        player_added=true
    else
        cmd="$cmd --player $other_player 2"
    fi
done

if [ "$player_added" = "false" ]; then
    cmd="$cmd --player $player 2"
fi
$cmd --length $L --memory_size $B --subjects $S --output_path "$output_root/complex_environment" --test_player $test_player $gui_flag

