from players.player_2.BaseStrategy import BaseStrategy


from models.item import Item
from models.player import Player


class Strategy2(BaseStrategy):
   def propose_item(self, player: Player, history: list[Item]) -> Item | None:
      # strategy 2 - focus on pauses and maximizing freshness
      
      # sort items in subject lists
      for key in player.sub_to_item:
         player.sub_to_item[key].sort(key=lambda x: x.importance)
      
      # checkgame start - send in an item with the best importance for a given preference level
      if len(history) == 0:
         return self._best_option_(player, player.sub_to_item)
      
      if history[-1] is not None:
         # we need to remove item from current suject list if it was said in prev room
         subjects = tuple(sorted(list(history[-1].subjects)))
         if subjects in player.sub_to_item and history[-1] in player.sub_to_item[subjects]:
            player.sub_to_item[subjects].pop()
            if len(player.sub_to_item[subjects]) == 0:
               del player.sub_to_item[subjects]
         return None

      # if history's last item was 'None' aka there was a pause -->
      # choose an item w/ subject(s) that have not been in the previous 5 terms
      if history[-1] is None:
         return self._freshness_(player, history)
      
      return None
   
   # returns the item with the highest importance from the subject with the highest preference
   def _best_option_(self, player: Player, sub_dictionary: list[Item]) -> Item | None:
      max_pref = 0
      max_key = tuple()
      for key in sub_dictionary:
         pref_score = 0.0
         for sub in key:
            pref_score += player.preferences.index(sub)
         pref_score = pref_score / len(key)
         if pref_score > max_pref:
            max_pref = pref_score
            max_key = key
      if max_key != () and len(sub_dictionary[max_key]) != 0:
         return sub_dictionary[max_key][-1]
      return None
   
   # general function for cases where freshness can be used
   def _freshness_(self, player: Player, history: list[Item]) -> Item | None:
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
         return self._best_option_(player, filtered_dict)
      ## case for if two pauses have just occurred - there is no item that would improve freshness - still should suggest something
      if len(history) > 1 and history[-2] is None:
         # suggest something unsaid from the memory bank
         item = self._best_option_(player, player.sub_to_item)
         if item is None and len(player.memory_bank) > 0:
            # if there is nothing left unsaid in the memory bank, say anything to prevent ending the convo early
            return player.memory_bank[0]
         return item