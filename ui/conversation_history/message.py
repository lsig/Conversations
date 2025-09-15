import pygame as pg

from models.item import Item
from ui.base import BLACK, WHITE, font


class Message(pg.sprite.Sprite):
	def __init__(
		self,
		item: Item,
		sender: str,
		x: int,
		y: int,
		max_width: int,
		bg_color: tuple = WHITE,
		*groups,
	) -> None:
		pg.sprite.Sprite.__init__(self, *groups)
		self.item = item
		self.sender = sender
		self.max_width = max_width
		self.padding = 10
		self.rect = pg.Rect(x, y, 0, 0)
		self.bg_color = bg_color

		self.text_font = font

		self.update()

	def update(self):
		if self.item is None:
			text_content = 'Pause...'
		else:
			item_id_short = str(self.item.id).split('-')[0]
			text_content = f'ID: {item_id_short} | Importance: {self.item.importance:.2f} | Subjects: {", ".join(map(str, self.item.subjects))}'

		sender_surface = self.text_font.render(f'{self.sender}', True, BLACK)
		text_surface = self.text_font.render(text_content, True, BLACK)

		content_height = sender_surface.get_height() + text_surface.get_height()

		self.image = pg.Surface((self.max_width, content_height + self.padding * 2), pg.SRCALPHA)

		self.rect.width = self.image.get_width()
		self.rect.height = self.image.get_height()

		pg.draw.rect(self.image, self.bg_color, self.image.get_rect(), border_radius=10)
		pg.draw.rect(self.image, BLACK, self.image.get_rect(), width=2, border_radius=10)
		self.image.blit(sender_surface, (self.padding, self.padding))
		self.image.blit(text_surface, (self.padding, self.padding + sender_surface.get_height()))
