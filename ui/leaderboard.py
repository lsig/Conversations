import pygame as pg

from ui.base import BLACK, WHITE


class Leaderboard(pg.sprite.Sprite):
	def __init__(
		self,
		score_data: dict,
		player_names: dict,
		x: int,
		y: int,
		width: int,
		height: int,
		*groups,
	):
		pg.sprite.Sprite.__init__(self, *groups)
		self.score_data = score_data
		self.player_names = player_names
		self.width = width
		self.height = height
		self.image = pg.Surface((width, height), pg.SRCALPHA)
		self.rect = self.image.get_rect(topleft=(x, y))

		self.title_font = pg.font.SysFont(None, 48, bold=True)
		self.header_font = pg.font.SysFont(None, 30, bold=True)
		self.data_font = pg.font.SysFont(None, 28)
		self.stats_font = pg.font.SysFont(None, 24)

		self.scroll_offset = 0
		self.content_height = 0

		self.padding = 40
		title_surface = self.title_font.render('Conversation Results', True, BLACK)
		stats_text = (
			f'Conversation Length: {self.score_data["conversation_length"]} turns '
			f'({self.score_data["pauses"]} pauses)'
		)
		stats_surface = self.stats_font.render(stats_text, True, BLACK)
		header_surface = self.header_font.render('Header', True, BLACK)

		self.content_y_start = (
			25
			+ title_surface.get_height()
			+ 10
			+ stats_surface.get_height()
			+ 30
			+ header_surface.get_height()
			+ 20
		)
		self.content_rect = pg.Rect(
			self.padding,
			self.content_y_start,
			self.width - self.padding * 2,
			self.height - self.content_y_start - 50,
		)

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
				max_scroll = max(0, self.content_height - visible_height)

				if event.button == 4:  # Scroll up
					self.scroll_offset = max(self.scroll_offset - 30, 0)
					self._update_display()
				elif event.button == 5:  # Scroll down
					self.scroll_offset = min(self.scroll_offset + 30, max_scroll)
					self._update_display()

	def _update_display(self):
		self.image.fill(WHITE)
		pg.draw.rect(self.image, BLACK, self.image.get_rect(), width=3, border_radius=15)

		title_surface = self.title_font.render('Conversation Results', True, BLACK)
		title_rect = title_surface.get_rect(centerx=self.rect.width / 2, top=25)
		self.image.blit(title_surface, title_rect)

		stats_text = (
			f'Conversation Length: {self.score_data["conversation_length"]} turns '
			f'({self.score_data["pauses"]} pauses)'
		)
		stats_surface = self.stats_font.render(stats_text, True, (100, 100, 100))
		stats_rect = stats_surface.get_rect(centerx=self.rect.width / 2, top=title_rect.bottom + 10)
		self.image.blit(stats_surface, stats_rect)

		headers_y = stats_rect.bottom + 30
		col_width = self.content_rect.width / 4
		headers = ['Player', 'Total Score per Turn', 'Shared Score', 'Individual Score']
		for i, header in enumerate(headers):
			header_surface = self.header_font.render(header, True, BLACK)
			header_rect = header_surface.get_rect(
				centerx=self.padding + col_width * (i + 0.5), y=headers_y
			)
			self.image.blit(header_surface, header_rect)

		line_y = headers_y + header_surface.get_height() + 10
		pg.draw.line(
			self.image,
			(200, 200, 200),
			(self.padding, line_y),
			(self.width - self.padding, line_y),
			2,
		)

		content_surface = pg.Surface(self.content_rect.size, pg.SRCALPHA)

		scores = self.score_data['player_scores']
		sorted_players = sorted(scores, key=lambda player: player['scores']['total'], reverse=True)

		y_offset = 0
		for player_data in sorted_players:
			player_id = player_data['id']
			player_name = self.player_names.get(player_id, 'Unknown')
			player_scores = player_data['scores']
			data_points = [
				player_name,
				f'{player_scores["total"]:.2f}',
				f'{player_scores["shared"]:.2f}',
				f'{player_scores["individual"]:.2f}',
			]

			for i, data in enumerate(data_points):
				data_surface = self.data_font.render(data, True, (50, 50, 50))
				data_rect = data_surface.get_rect(
					centerx=col_width * (i + 0.5), y=y_offset - self.scroll_offset
				)
				content_surface.blit(data_surface, data_rect)

			y_offset += self.data_font.get_height() + 15

		self.content_height = y_offset
		self.image.blit(content_surface, self.content_rect.topleft)

	def draw(self, surface: pg.Surface):
		surface.blit(self.image, self.rect)
