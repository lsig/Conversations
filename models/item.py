import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
	id: uuid.UUID
	player_id: uuid.UUID
	importance: float
	subjects: tuple[int, ...]
