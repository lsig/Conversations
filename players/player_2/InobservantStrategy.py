from models.item import Item
from models.player import Player
from players.player_2.BaseStrategy import BaseStrategy


class InobservantStrategy(BaseStrategy):
    # this is the case where we have a large number of bad actor players that mess up the game -> this strategy is called
    # Inobservant is more agressive than Observant - it handles pauses, but wants to keep the convo going if possible
    # random players, random pause players, and others that say random items - chances are - score will be quite low if they are allowed to speak
    # pause (slight chance) - always suggest an item, ideally FRESH, then by COHERENCE possibility, to start a story
    # previous item (not ours) - always (?) suggest an item if it can lower the coherence score to 0 in the window
    # otherwise stay silent??
    # ideal (preference in code - memory bank with multiple items) - start a story and keep talking for as long as possible
    # previous item (ours) - try to be coherent, otherwise start a new topic that is PREFERRED - not good to lose the 50% chance of speaking
    # other considerations:
        # conversation length is long - random players will always suggest items, even if they used them already, so convo could go to end
        # if we run out of items, the score could be very low
        # may need to 'rest' for certain periods - but for how long????
        # mitigated with an observation period first (sort of)
        # should we take breaks?????? - have a story, then pause for some fraction of the conversation (based on memory bank length)
        # then keep going
        # say length is L --> and memory bank is B. How should we spread out -> Want to say 3 items for a story, get a relatively good coherence
        # B/3 is possible number of "good" stories --> so size of break is L/3/B
    def propose_item(self, player: Player, history: list[Item]) -> Item | None:
        turn_nr = len(history) + 1
        num_p = self.player.number_of_players

        # Don't propose if no items left
        if len(player.sub_to_item) == 0:
            return None
        
        # Remove if proposal was accepted last turn
        if turn_nr > 1 and history[-1] is not None and history[-1] == player.last_proposed_item:
            last_proposed_subjects = tuple(sorted(list(player.last_proposed_item.subjects)))
            self._remove_item_from_dict(player, last_proposed_subjects)

			# If we still have items with those subjects, propose the most valuable one
            if (
				last_proposed_subjects in player.sub_to_item
				and len(player.sub_to_item[last_proposed_subjects]) != 0
			):
                most_valuable_item = max(
				player.sub_to_item[last_proposed_subjects],
				key=lambda item: self._get_imp_pref_score(item, player),
                )
				# print(f"Most valuable item: {most_valuable_item}")
                player.last_proposed_item = most_valuable_item
                return most_valuable_item
        
        # Observe for obs_num turns
        if turn_nr <= self.obs_num:
            # If last turn the second pause occurred then try to be coherent no matter what
            if len(history) > 0 and history[-1] is None and history.count(None) == 2:
                return self._propose_coherently(player, history)
            if num_p > 2 and (turn_nr == 1 or (turn_nr > 1 and history[-1] is not None)):
				# in observation period and other people are talking - so don't propose anything
                return None
        
        # go for freshness after a pause if possible
        if turn_nr > 1 and history[-1] is None:
            proposed_item = self._propose_freshly(player, history)
            return proposed_item
        else:
            # go for coherence when possible to do so
            proposed_item = self._propose_coherently(player, history)
            return proposed_item
    
    def _remove_item_from_dict(self, player: Player, subjects: tuple[int, ...]) -> None:
        player.sub_to_item[subjects].remove(player.last_proposed_item)
        if len(player.sub_to_item[subjects]) == 0:
            del player.sub_to_item[subjects]
    
    # propose freshly - if there is a pause - immediately attempt to take convo back if possible
    # finds item to maximize freshness
	# make a copy and sort? Probably a better idea
    def _propose_freshly(self, player, history) -> Item | None:
		# collect all subjects in previous 5 turns in prev_subs
        prev_subs = []
        filtered_dict = player.sub_to_item.copy()
        for sub in history[-5:]:
            if sub is not None:
                prev_subs.append(sub)
		# filter out all items with subjects that were previously mentioned in past 5 turns
        for sub in prev_subs:
            filtered_dict = dict(filter(lambda x: sub not in x[0], filtered_dict.items()))
		
        if len(filtered_dict) != 0:
			# maximize freshness - grab items with 2 subjects if possible, else grab items with 
            sub_length = 0
            sub_key = tuple()
            for key in filtered_dict:
                if len(filtered_dict[key]) > sub_length:
                    sub_length = len(filtered_dict[key])
                    sub_key = key
			# TODO: Output item from this subject with highest importance
            player.last_proposed_item = filtered_dict[sub_key][0]
            return player.last_proposed_item
		# otherwise propose an option that will allow a story to be told
        else:
            return self._propose_possible_coherence(player)
    
    # TODO - fix???? Should ouput all items? Should not matter because it just iterates through the subjects of sub_to_item???
	# proposes item with the highest probability of future coherence 
    def _propose_possible_coherence(self, player) -> Item | None:
        _, next_items = next(iter(player.sub_to_item.items()))

		# Pick the most valuable item
        most_valuable_item = max(
			next_items, key=lambda item: self._get_imp_pref_score(item, player)
		)
        player.last_proposed_item = most_valuable_item
        return most_valuable_item
    
    # proposes an item that is coherent
    def _propose_coherently(self, player, history) -> Item | None:
        # stub
        return None

