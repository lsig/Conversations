import openai

from models.player import Item, Player, PlayerSnapshot

openai_api_key_player_4: str = 'sk-REDACTED'


class Player4(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)

		self.client = openai.OpenAI(api_key=openai_api_key_player_4)

	def propose_item(self, history: list[Item]) -> Item | None:
		prompt = self.create_prompt(
			self.preferences, self.memory_bank, self.conversation_length, history
		)
		print('Sending prompt!')
		response = self.client.responses.create(
			model='gpt-4.1',
			input=prompt,
			max_output_tokens=16,
		)
		print(f'Received response: {response.output_text}')
		if response.output_text == 'None':
			return None
		try:
			index = int(response.output_text)
			if 0 <= index < len(self.memory_bank):
				return self.memory_bank[index]
			else:
				return None
		except ValueError:
			return None

	def create_prompt(
		self,
		preferences: list[int],
		memory_bank: list[Item],
		conversation_length: int,
		history: list[Item],
	) -> str:
		prompt = f"""
            There are some players, and every player has a random memory bank of newsworthy items that they could contribute to the conversation. Every item has an importance. The conversation has a fixed length L, {conversation_length}.

            On each turn, each player may propose to share an item. If multiple players attempt to contribute an item: If the player currently talking wants to contribute again, they will be chosen with probability 0.5. If the player currently talking is not chosen, then a player at random from among those who propose an item and have so far contributed the smallest number of items among that group will be selected. If nobody contributes anything, then the sequence is filled by a "pause". If there are three consecutive pauses, then the conversation ends prematurely.

            The shared goals of a conversation are as follows:

            Coherence
            For every item I, the (up to) 3 preceding items and (up to) 3 following items are collected into a set CI of context items. If a subject of I is never mentioned in CI then one point is lost from the final score. If all subjects in I are mentioned at least twice in CI then one point is added to the final score. The window defining CI does not extend beyond the start of the conversation or any pauses.
            Importance
            The total importance of all items in the final item sequence is added to the shared score. (Everybody agrees about the importance of each item.)
            Nonrepetition
            An item that is repeated has zero importance and does not contribute to the coherence score after the first instance of the item.
            Freshness
            Immediately after a pause, an item with a subject that was not previously present in the 5 turns prior to the pause gets a point added to the final score. An item with two novel subjects of this sort gets two bonus points. Repeated items do not get freshness points.
            Nonmonotonousness
            An item with a subject that was also present in each of the previous three items leads to the loss of a point. Also, repeated items lose one point, since the audience has already heard that news.
            Individual goals depend on each player's preferred topics of conversation. The simulator gives each player a random permutation of the S subjects that represents the ranked preference of that player. An item with a subject that is of rank k for that player achieves a bonus of 1-k/|S| where |S| is the total number of possible subjects. An item with two subjects gives the player a bonus corresponing to the average of the two individual bonuses. Players know their own ranking, but not the ranking of other players.

            At the end of the game, the total score for each player is divided by L, resulting in an overall conversation quality that is the final metric by which players will be compared.

            You are a player in this game. Your goal is to select an item from your memory bank, or return "None" to pass, in order to achieve the highest conversation quality.
            
            The conversation so far is as follows:
            {len(history)} items have been proposed in total: {', '.join('[' + 'subjects: ' + str(item.subjects) + ', importance: ' + str(item.importance) + ']' for item in history)}.
            
            Your memory bank contains the following items:
            {', '.join('[' + 'id: ' + str(item.id) + ', subjects: ' + str(item.subjects) + ', importance: ' + str(item.importance) + ']' for item in memory_bank)}.
            
            Your preferences for subjects are as follows:
            {', '.join('subject: ' + str(subject) + ', rank: ' + str(rank) for rank, subject in enumerate(preferences))}

            Based on the conversation so far, your memory bank, and your subject preferences, which item will you propose to contribute next? If you do not want to contribute an item, respond with "None". Otherwise, respond with the index of the item you wish to contribute, in your memory bank. Do not return anything other than either "None" or an integer index.
        """
		return prompt
