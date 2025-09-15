# In ui/turn_display.py

import pygame as pg

from ui.base import BLACK, WHITE

GREY = (200, 200, 200)
DARK_GREY = (100, 100, 100)
GREEN = (20, 150, 20)
RED = (200, 20, 20)


class TurnDisplay(pg.sprite.Sprite):
	def __init__(self, x: int, y: int, width: int, height: int, *groups) -> None:
		pg.sprite.Sprite.__init__(self, *groups)
		self.x = x
		self.y = y
		self.width = width
		self.height = height
		self.rect = pg.Rect(x, y, width, height)

		self.header_font = pg.font.SysFont(None, 32, bold=True)
		self.title_font = pg.font.SysFont(None, 28, bold=True)
		self.label_font = pg.font.SysFont(None, 24)
		self.score_font = pg.font.SysFont(None, 24, bold=True)
		self.status_font = pg.font.SysFont(None, 32, bold=True)
		self.penalty_font = pg.font.SysFont(None, 22, bold=True)

		self.turn_info = {}
		self.image = pg.Surface((width, height), pg.SRCALPHA)
		self.update_display()

	def update_info(self, turn_info: dict):
		self.turn_info = turn_info if turn_info else {}
		self.update_display()

	def _render_text(self, text, font, color, x, y, align='left'):
		text_surface = font.render(text, True, color)
		text_rect = text_surface.get_rect()
		if align == 'left':
			text_rect.topleft = (x, y)
		elif align == 'center':
			text_rect.centerx = x
			text_rect.top = y
		elif align == 'right':
			text_rect.topright = (x, y)
		self.image.blit(text_surface, text_rect)
		return text_rect

	def update_display(self):
		self.image.fill(WHITE)
		pg.draw.rect(self.image, BLACK, self.image.get_rect(), width=2, border_radius=10)

		padding = 15
		y_offset = padding

		turn_text = f'Turn: {self.turn_info.get("turn", 0)}'
		y_offset += (
			self._render_text(
				turn_text, self.header_font, BLACK, self.width / 2, y_offset, align='center'
			).height
			+ 10
		)

		pg.draw.line(self.image, GREY, (padding, y_offset), (self.width - padding, y_offset), 2)
		y_offset += 10
		self._render_text(
			'Turn Impact',
			self.title_font,
			BLACK,
			self.width / 2,
			y_offset,
			align='center',
		)
		y_offset += self.title_font.get_height() + 15

		if not self.turn_info:
			self._render_text(
				'--- START ---',
				self.status_font,
				DARK_GREY,
				self.width / 2,
				y_offset + 30,
				align='center',
			)
			return

		elif self.turn_info.get('item') is None:
			self._render_text(
				'PAUSE', self.status_font, DARK_GREY, self.width / 2, y_offset + 30, align='center'
			)
			return
		else:
			score_impact = self.turn_info.get('score_impact', {})
			col1_x = padding + 20
			col2_x = self.width - padding - 20

			score_items = {
				'Importance': score_impact.get('importance', 0.0),
				'Coherence (Prov.)': score_impact.get('coherence', 0.0),
				'Freshness': score_impact.get('freshness', 0.0),
				'Non-monotonousness': score_impact.get('nonmonotonousness', 0.0),
				'Individual Bonus': score_impact.get('individual', 0.0),
			}

			for label, value in score_items.items():
				color = GREEN if value > 0 else (RED if value < 0 else BLACK)
				self._render_text(f'{label}:', self.label_font, BLACK, col1_x, y_offset)
				rect = self._render_text(
					f'{value:+.2f}', self.score_font, color, col2_x, y_offset, align='right'
				)
				y_offset += rect.height + 5

			y_offset += 10

			total_delta = score_impact.get('total', 0.0)
			total_color = GREEN if total_delta > 0 else (RED if total_delta < 0 else BLACK)
			self._render_text('Total Shared Delta:', self.title_font, BLACK, col1_x, y_offset)
			self._render_text(
				f'{total_delta:+.2f}', self.title_font, total_color, col2_x, y_offset, align='right'
			)
			y_offset += self.title_font.get_height() + 15

	def draw(self, surface: pg.Surface):
		surface.blit(self.image, self.rect)
