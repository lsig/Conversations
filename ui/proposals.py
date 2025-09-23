import pygame as pg

from ui.base import BLACK, WHITE
from ui.conversation_history.message import Message


class Proposals(pg.sprite.Sprite):
	def __init__(self, x: int, y: int, width: int, height: int, *groups) -> None:
		pg.sprite.Sprite.__init__(self, *groups)
		self.width = width
		self.height = height
		self.image = pg.Surface((width, height), pg.SRCALPHA)
		self.rect = self.image.get_rect(topleft=(x, y))

		self.title_font = pg.font.SysFont(None, 24, bold=True)
		self.scroll_offset = 0
		self.messages: list[Message] = []
		self._total_height = 0
		self.turn_info = {}
		self.player_names = {}
		self.padding = 10

		title_surface = self.title_font.render('Proposals', True, BLACK)
		self.title_height_offset = title_surface.get_height() + self.padding * 2

		self.content_rect = pg.Rect(
			self.padding,
			self.title_height_offset,
			self.width - self.padding * 2,
			self.height - self.title_height_offset - self.padding,
		)
		self._update_display()

	def update_info(self, turn_info: dict, player_names: dict):
		self.turn_info = turn_info
		self.player_names = player_names
		self.scroll_offset = 0
		self._update_display()

	def _update_display(self):
		self.messages = []
		self._total_height = 0
		spacing = 5

		if self.turn_info and 'proposals' in self.turn_info:
			y_offset = 0
			for player_id, item in self.turn_info['proposals'].items():
				if item:
					speaker_name = self.player_names.get(player_id, 'Unknown')
					message = Message(item, speaker_name, 0, 0, self.content_rect.width)
					self.messages.append(message)
					y_offset += message.rect.height + spacing
			self._total_height = y_offset

		self.image.fill(WHITE)
		pg.draw.rect(self.image, BLACK, self.image.get_rect(), width=2, border_radius=10)

		title_surface = self.title_font.render('Proposals', True, BLACK)
		title_rect = title_surface.get_rect(centerx=self.width / 2, top=self.padding)
		self.image.blit(title_surface, title_rect)

		content_surface = pg.Surface(self.content_rect.size, pg.SRCALPHA)

		y_offset = 0 - self.scroll_offset
		for message in self.messages:
			content_surface.blit(message.image, (0, y_offset))
			y_offset += message.rect.height + spacing

		self.image.blit(content_surface, self.content_rect.topleft)

	def handle_event(self, event):
		if event.type == pg.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
			content_screen_rect = self.content_rect.copy()
			content_screen_rect.topleft = (
				self.rect.x + self.content_rect.x,
				self.rect.y + self.content_rect.y,
			)
			if content_screen_rect.collidepoint(event.pos):
				visible_height = self.content_rect.height
				max_scroll = max(0, self._total_height - visible_height)

				if event.button == 4:
					self.scroll_offset = max(self.scroll_offset - 20, 0)
					self._update_display()
				elif event.button == 5:
					self.scroll_offset = min(self.scroll_offset + 20, max_scroll)
					self._update_display()

	def draw(self, surface: pg.Surface):
		surface.blit(self.image, self.rect)
