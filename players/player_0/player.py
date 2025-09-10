from models.player import Item, Player, PlayerSnapshot


class Player0(Player):
    def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
        super().__init__(snapshot, conversation_length)

    def propose_item(self, history: list[Item]) -> Item | None:
        """Propose the most important unused item from the memory bank."""
        used_ids = {item.id for item in history}
        unused = [item for item in self.memory_bank if item.id not in used_ids]

        if not unused:
            return None

        return max(unused, key=lambda i: i.importance)
