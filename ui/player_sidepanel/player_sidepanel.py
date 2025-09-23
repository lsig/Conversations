import pygame as pg

from models.player import Player
from ui.base import BLACK, WHITE
from ui.player_sidepanel.player_info import PlayerInfo


class PlayerSidepanel(pg.sprite.Sprite):
	def __init__(
		self,
		players: list[Player],
		player_contributions: dict,
		x: int,
		y: int,
		width: int,
		height: int,
		*groups,
	) -> None:
		pg.sprite.Sprite.__init__(self, *groups)
		self.players = players
		self.player_contributions = player_contributions
		self.width = width
		self.height = height
		self.image = pg.Surface((width, height), pg.SRCALPHA)
		self.rect = self.image.get_rect(topleft=(x, y))

		self.cards = pg.sprite.Group()
		self.scroll_offset = 0
		self.padding = 10

		self.title_font = pg.font.SysFont(None, 24, bold=True)
		title_surface = self.title_font.render('Players', True, BLACK)
		self.title_height_offset = title_surface.get_height() + self.padding * 2

		self.content_rect = pg.Rect(
			self.padding,
			self.title_height_offset,
			self.width - self.padding * 2,
			self.height - self.title_height_offset - self.padding,
		)

		self.create_cards()

	def create_cards(self):
		y_offset = 0
		spacing = 10

		for player in self.players:
			count = len(self.player_contributions.get(player.id, []))
			card = PlayerInfo(
				player=player, x=0, y=y_offset, width=self.content_rect.width, contributions=count
			)
			y_offset += card.rect.height + spacing
			self.cards.add(card)

		self.content_height = y_offset

	def update_contributions(self, contributions: dict):
		self.player_contributions = contributions
		for card in self.cards:
			count = len(self.player_contributions.get(card.player.id, []))
			card.set_contributions(count)

	def handle_event(self, event):
		if event.type == pg.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
			content_screen_rect = self.content_rect.copy()
			content_screen_rect.topleft = (
				self.rect.x + self.content_rect.x,
				self.rect.y + self.content_rect.y,
			)

			if content_screen_rect.collidepoint(event.pos):
				if event.button == 4:
					self.scroll_offset = min(self.scroll_offset + 20, 0)
				elif event.button == 5:
					visible_height = self.content_rect.height
					max_scroll = max(0, self.content_height - visible_height)
					self.scroll_offset = max(self.scroll_offset - 20, -max_scroll)
				elif event.button == 1:
					local_pos = (
						event.pos[0] - content_screen_rect.x,
						event.pos[1] - content_screen_rect.y - self.scroll_offset,
					)
					for card in self.cards:
						if card.rect.collidepoint(local_pos):
							return card.player

	def update(self):
		self.image.fill(WHITE)
		pg.draw.rect(self.image, BLACK, self.image.get_rect(), width=2, border_radius=10)

		title_surface = self.title_font.render('Players', True, BLACK)
		title_rect = title_surface.get_rect(centerx=self.width / 2, top=self.padding)
		self.image.blit(title_surface, title_rect)

		content_surface = pg.Surface(self.content_rect.size, pg.SRCALPHA)
		content_surface.fill(WHITE)

		for card in self.cards:
			content_surface.blit(card.image, (card.rect.x, card.rect.y + self.scroll_offset))

		self.image.blit(content_surface, self.content_rect.topleft)

	def draw(self, surface: pg.Surface):
		surface.blit(self.image, self.rect)
