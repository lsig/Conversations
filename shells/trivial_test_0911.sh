
#          ◅▯◊║◊▯▻   Global Setting   ◅▯◊║◊▯▻

# player to teset (primary focus player)
# test_player="p_bst_medium"

test_player="p_balanced_greedy"

# global setting: (default L 10, B 10, S 20)
L=200  
B=500
S=20

# derived round/output settings
root="results"
round_name="test_good_players_0913_${test_player}"
# round_name="test_threhold_3rounds_0912_${test_player}"
output_root="$root/${round_name}_L${L}B${B}S${S}"

# test mode control
gui_on="false"  
rounds=10 # random rounds with same setting. 
detailed_on="true" # detailed

# Set GUI flag based on gui_on variable
if [ "$gui_on" = "true" ]; then
    gui_flag="--gui"
else
    gui_flag=""
fi


if [ "$detailed_on" = "true" ]; then
    detailed_flag="--detailed"
else
    detailed_flag=""
fi

rounds_flag="--rounds $rounds"

#          ◅▯◊║◊▯▻   Test Case   ◅▯◊║◊▯▻

# # collaboration
python main.py --player $test_player 10 --length $L --memory_size $B --subjects $S --output_path "$output_root/self_collaboration" --test_player $test_player $gui_flag $rounds_flag $detailed_flag


# # against random player
python main.py --player $test_player 2 --player pr 8 --length $L --memory_size $B --subjects $S --output_path "$output_root/against_random_player" --test_player $test_player $gui_flag $rounds_flag $detailed_flag


# complex environment
# include: pr, p_zipper, p_selfless_greedy, p_selfish_greedy, p_bst_low, p_bst_medium, p_bst_high
# player_list="pr p_zipper p_selfless_greedy p_selfish_greedy p_balanced_greedy p_bst_low p_bst_medium p_bst_high"
# player_list="pr p_zipper p_selfless_greedy p_selfish_greedy p_balanced_greedy p_bst_low p_bst_medium"
player_list="p_zipper p_selfless_greedy p_balanced_greedy p_bst_low"

cmd="python main.py"
player_added=false

for other_player in $player_list; do
    if [ "$other_player" = "$test_player" ]; then
        cmd="$cmd --player $other_player 4"
        player_added=true
    else
        cmd="$cmd --player $other_player 2"
    fi
done

if [ "$player_added" = "false" ]; then
    cmd="$cmd --player $test_player 2"
fi
$cmd --length $L --memory_size $B --subjects $S --output_path "$output_root/complex_environment" --test_player $test_player $gui_flag $rounds_flag $detailed_flag


