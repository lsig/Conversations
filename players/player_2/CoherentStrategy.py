from collections import Counter
import random

from models.item import Item
from models.player import Player
from players.player_2.BaseStrategy import BaseStrategy
from players.player_2.Strategy_1 import Strategy_1


class CoherentStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.obs_num = 0    
        self.strategy1 = Strategy_1()

    def propose_item(self, player: Player, history: list[Item]) -> Item | None:
        turn_nr = len(history) + 1

        # Determine observation period
        num_p = player.number_of_players
        c_len = player.conversation_length
        self.obs_num = num_p
        if num_p - 1 > c_len/2:
                self.obs_num = c_len//2

        # Remove if proposal was accepted last turn
        if turn_nr > 1 and history[-1] == player.last_proposed_item:

            last_proposed_subjects = tuple(sorted(list(player.last_proposed_item.subjects)))
            player.sub_to_item[last_proposed_subjects].remove(player.last_proposed_item)

            # If we still have items with those subjects, propose the most valuable one
            if (
                last_proposed_subjects in player.sub_to_item
                and len(player.sub_to_item[last_proposed_subjects]) != 0
            ):
                # print(f"Still have items with subjects {player.sub_to_item[last_proposed_subjects]}")
                most_valuable_item = max(
                    player.sub_to_item[last_proposed_subjects],
                    key=lambda item: self._get_overall_score(item, player),
                )
                # print(f"Most valuable item: {most_valuable_item}")
                player.last_proposed_item = most_valuable_item
                return most_valuable_item
            
        # Observe
        if turn_nr <= self.obs_num:
            # If last turn the second pause occurred then try to be coherent no matter what
            if history[-1] is None and history.count(None) == 2:
                return self.strategy1.propose_item(player, history)
                
            if num_p > 2 and (turn_nr == 1 or (turn_nr > 1 and history[-1] is not None)):
                # in observation period and other people are talking - so don't propose anything
                return None

        else:
            # if there was a pause --> go for freshness
            context = history[-3:]
            # Context doesn't extend over pause
            if None in context:
                context = context[context.index(None) + 1 :]

            context_subs_sorted = self._get_subjects_counts_sorted(context, player)
            print(f"Sorted: {context_subs_sorted}")

            # Go through all subjects in context, sorted according to frequency in context and then by number of items in own memory bank
            # If there are no items in memory bank that match the subjects in context, then pause
            for subs, subs_count in context_subs_sorted:
                # If a subject already occurred thrice then we don't want to be monotonous
                if subs_count < 3:
                    items_with_subs = player.sub_to_item.get(subs, []).copy()
                    # If there is only one subject, also get items with two subjects including that subject
                    if len(subs) == 1:
                        # print(f"Also look for items with subject {subs} and another subject")
                        items_with_subs.extend(
                            [
                                item
                                for items_subs, items in player.sub_to_item.items()
                                if subs[0] in items_subs
                                for item in items
                            ]
                        )

                    # If the subject only occurred once in the context and we only have one item with this subject, propose it with 50/50 chance
                    if subs_count == 1 and len(items_with_subs) == 1 and random.uniform(0, 1) < 0.5:
                        continue 

                    # print(f"Items with subjects {subs}: {items_with_subs}")
                    # If we have an item with fitting subjects, propose the most valuable one
                    if items_with_subs:
                        most_valuable_item = max(
                            items_with_subs, key=lambda item: self._get_overall_score(item, player)
                        )
                        player.last_proposed_item = most_valuable_item

                        # print(f"Most valuable item: {most_valuable_item}")
                        return most_valuable_item

            return None
        
    def _get_subjects_counts_sorted(self, items: list[Item], player: Player) -> list:
        """Count occurrences of subjects in items and return them, first sorted by count, second sorted by occurence in player's memory bank."""

        subs_count = Counter()
        for item in items:
            if item is not None:
                subs_count.update(item.subjects)
                if len(item.subjects) == 2:
                    subs_count[item.subjects] += 1

        subs_sorted_by_count = sorted(
            (
                (subs if isinstance(subs, tuple) else (subs,), count)
                for subs, count in subs_count.items()
            ),
            key=lambda x: (
                -x[1],
                -len(player.sub_to_item[x[0]]) if x[0] in player.sub_to_item else 0,
            ),
        )

        return subs_sorted_by_count
    
    def _get_overall_score(self, item: Item, player: Player) -> float:
        """Calculate overall score of an item based on its importance and individual bonuses."""

        item_bonuses = [
            1 - (player.preferences.index(sub)) / player.subject_num for sub in item.subjects
        ]
        final_bonus = sum(item_bonuses) / len(item_bonuses)

        overall_score = item.importance + final_bonus
        return overall_score
    
    # finds item to maximize freshness
    # make a copy and sort? Probably a better idea
    def _freshness(self, player, history) -> Item | None:
        prev_subs = []
        filtered_dict = player.sub_to_item.copy()
        if len(history) > 1 and history[-2] is not None:
            for sub in history[-2].subjects:
                prev_subs.append(sub)
        if len(history) > 2 and history[-3] is not None:
            for sub in history[-3].subjects:
                prev_subs.append(sub)
        if len(history) > 3 and history[-4] is not None:
            for sub in history[-4].subjects:
                prev_subs.append(sub)
        if len(history) > 4 and history[-5] is not None:
            for sub in history[-5].subjects:
                prev_subs.append(sub)
        for sub in prev_subs:
            filtered_dict = dict(filter(lambda x: sub not in x[0], filtered_dict.items()))
        if len(filtered_dict) != 0:
            # maximize freshness if posible - find subject with most items in filtered_dict
            sub_length = 0
            sub_key = tuple()
            for key in filtered_dict:
                if len(filtered_dict[key]) > sub_length:
                    sub_length = len(filtered_dict[key])
                    sub_key = key
            player.last_proposed_item = filtered_dict[sub_key][0]
            return player.last_proposed_item
        # otherwise there was no fresh option be greedy
        return self._greedy(player, history)
    
    def _greedy(self, player, history) -> Item | None:
        _, coherent_items = next(iter(player.sub_to_item.items()))

        # Pick the most valuable item
        most_valuable_item = max(
            coherent_items, key=lambda item: self._get_overall_score(item, player)
        )
        player.last_proposed_item = most_valuable_item
