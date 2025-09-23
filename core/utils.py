import json
import uuid

from models.item import Item


class CustomEncoder(json.JSONEncoder):
	def _sanitize_keys(self, obj):
		if isinstance(obj, dict):
			return {str(k): self._sanitize_keys(v) for k, v in obj.items()}
		if isinstance(obj, list):
			return [self._sanitize_keys(elem) for elem in obj]
		return obj

	def default(self, obj):
		if isinstance(obj, Item):
			return {
				'id': str(obj.id),
				'player_id': str(obj.player_id),
				'importance': obj.importance,
				'subjects': obj.subjects,
			}
		if isinstance(obj, uuid.UUID):
			return str(obj)

		return super().default(obj)

	def encode(self, obj):
		sanitized_obj = self._sanitize_keys(obj)
		return super().encode(sanitized_obj)
