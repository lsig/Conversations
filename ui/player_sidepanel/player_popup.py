import pygame as pg

from models.player import Player
from ui.base import BLACK, WHITE, font
from ui.conversation_history.message import Message


class PlayerPopup(pg.sprite.Sprite):
	def __init__(self, player: type[Player], x: int, y: int, width: int, height: int, *groups):
		pg.sprite.Sprite.__init__(self, *groups)
		self.player = player
		self.width = width
		self.height = height
		self.rect = pg.Rect(x, y, width, height)
		self.image = pg.Surface((width, height), pg.SRCALPHA)
		self.scroll_offset = 0
		self.popup_total_height = 0
		self.memory_bank_messages = []
		self.title_font = pg.font.SysFont(None, 24, bold=True)
		self.font = font
		self._update_popup_content()

	def _update_popup_content(self):
		self.memory_bank_messages = []
		self.popup_total_height = 0

		popup_padding = 10
		message_spacing = 5

		y_offset = 0
		if self.player:
			for item in self.player.memory_bank:
				message = Message(
					item=item,
					sender='Memory Item',
					x=0,
					y=0,
					max_width=self.width - popup_padding * 2,
				)
				self.memory_bank_messages.append(message)
				y_offset += message.rect.height + message_spacing

		self.popup_total_height = y_offset

	def handle_event(self, event):
		if event.type == pg.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
			if event.button == 4:
				self.scroll_offset = max(0, self.scroll_offset - 20)
			elif event.button == 5:
				messages_content_height = (
					self.height
					- (self.title_font.get_height() + 10)
					- (self.font.get_height() + 5)
					- 20
				)
				max_scroll = max(0, self.popup_total_height - messages_content_height)
				self.scroll_offset = min(max_scroll, self.scroll_offset + 20)

	def draw(self, surface: pg.Surface):
		self.image.fill(WHITE)
		pg.draw.rect(self.image, BLACK, self.image.get_rect(), width=2, border_radius=10)

		player_name = f'{self.player.name}'
		title_surface = self.title_font.render(player_name, True, BLACK)
		title_rect = title_surface.get_rect(centerx=self.width / 2, top=10)
		self.image.blit(title_surface, title_rect)

		info_text = f'Preferences: {", ".join(map(str, self.player.preferences))}'
		info_surface = self.font.render(info_text, True, BLACK)
		info_rect = info_surface.get_rect(left=10, top=title_rect.bottom + 5)
		self.image.blit(info_surface, info_rect)

		messages_content_rect = pg.Rect(
			10, info_rect.bottom + 5, self.width - 20, self.height - info_rect.bottom - 15
		)
		messages_content_surface = pg.Surface(
			(messages_content_rect.width, messages_content_rect.height), pg.SRCALPHA
		)

		y_offset = -self.scroll_offset
		for message in self.memory_bank_messages:
			messages_content_surface.blit(message.image, (0, y_offset))
			y_offset += message.rect.height + 5

		self.image.blit(messages_content_surface, messages_content_rect.topleft)
		surface.blit(self.image, self.rect)
