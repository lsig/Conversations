import pygame as pg

from ui.base import BLACK, LIGHT_GREEN, LIGHT_GREY, LIGHT_RED, WHITE
from ui.conversation_history.message import Message


class ConversationHistory(pg.sprite.Sprite):
	def __init__(self, x: int, y: int, width: int, height: int, *groups):
		pg.sprite.Sprite.__init__(self, *groups)
		self.width = width
		self.height = height
		self.image = pg.Surface((self.width, self.height), pg.SRCALPHA)
		self.rect = self.image.get_rect(topleft=(x, y))

		self.messages: list[Message] = []
		self._total_height = 0
		self.scroll_offset = 0
		self.message_spacing = 5
		self.padding = 10

		self.title_font = pg.font.SysFont(None, 24, bold=True)
		title_surface = self.title_font.render('Conversation History', True, BLACK)
		self.title_height_offset = title_surface.get_height() + self.padding * 2

		self.content_rect = pg.Rect(
			self.padding,
			self.title_height_offset,
			self.width - self.padding * 2,
			self.height - self.title_height_offset - self.padding,
		)
		self._update_display()

	def add_message(self, turn_result: dict):
		item = turn_result.get('item')
		sender = turn_result.get('speaker_name', 'Pause')
		score_impact = turn_result.get('score_impact', {})

		message_color = WHITE
		if item is None:
			message_color = LIGHT_GREY
		else:
			total_delta = score_impact.get('total', 0.0)
			if total_delta > 0:
				message_color = LIGHT_GREEN
			elif total_delta < 0:
				message_color = LIGHT_RED

		new_message = Message(
			item=item,
			sender=sender,
			x=0,
			y=0,
			max_width=self.content_rect.width,
			bg_color=message_color,
		)

		self.messages.insert(0, new_message)
		self._total_height = sum(m.rect.height + self.message_spacing for m in self.messages)
		self.scroll_offset = 0
		self._update_display()

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
				elif event.button == 5:
					self.scroll_offset = min(self.scroll_offset + 20, max_scroll)

				self._update_display()

	def _update_display(self):
		self.image.fill(WHITE)
		pg.draw.rect(self.image, BLACK, self.image.get_rect(), width=2, border_radius=10)

		title_surface = self.title_font.render('Conversation History', True, BLACK)
		title_rect = title_surface.get_rect(centerx=self.width / 2, top=self.padding)
		self.image.blit(title_surface, title_rect)

		content_surface = pg.Surface(self.content_rect.size, pg.SRCALPHA)

		y_offset = 0 - self.scroll_offset
		for message in self.messages:
			content_surface.blit(
				message.image,
				(0, y_offset),
			)
			y_offset += message.rect.height + self.message_spacing

		self.image.blit(content_surface, self.content_rect.topleft)

	def draw(self, surface: pg.Surface):
		surface.blit(self.image, self.rect)

	def clear(self):
		self.messages.clear()
		self._total_height = 0
		self.scroll_offset = 0
		self._update_display()
