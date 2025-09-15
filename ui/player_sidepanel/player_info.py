import pygame as pg

from models.player import Player
from ui.base import BLACK, WHITE, font


class PlayerInfo(pg.sprite.Sprite):
	def __init__(
		self, player: type[Player], x: int, y: int, width: int, contributions: int, *groups
	) -> None:
		pg.sprite.Sprite.__init__(self, *groups)
		self.player = player
		self.card_width = width
		self.card_height = 60
		self.image = pg.Surface((self.card_width, self.card_height), pg.SRCALPHA)
		self.rect = self.image.get_rect(topleft=(x, y))
		self.contributions = contributions
		self._render()

	def set_contributions(self, count: int):
		if self.contributions != count:
			self.contributions = count
			self._render()

	def _render(self):
		self.image.fill(WHITE)

		pg.draw.rect(
			surface=self.image,
			color=BLACK,
			rect=(0, 0, self.card_width, self.card_height),
			width=2,
			border_radius=10,
		)

		name_text = font.render(f'{self.player.name}', True, BLACK)
		name_rect = name_text.get_rect(centerx=self.card_width // 2, top=10)
		contrib_text = font.render(f'Contributions: {self.contributions}', True, BLACK)
		contrib_rect = contrib_text.get_rect(
			centerx=self.card_width // 2, bottom=self.card_height - 10
		)

		self.image.blit(name_text, name_rect)
		self.image.blit(contrib_text, contrib_rect)
