import sys

import pygame as pg

from core.engine import Engine
from ui.base import SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from ui.conversation_history.conversation_history import ConversationHistory
from ui.leaderboard import Leaderboard
from ui.player_sidepanel.player_popup import PlayerPopup
from ui.player_sidepanel.player_sidepanel import PlayerSidepanel
from ui.proposals import Proposals
from ui.turn_display import TurnDisplay


class Game:
	def __init__(self, engine: Engine):
		pg.init()
		pg.display.set_caption('Conversations')

		self.screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
		self.engine = engine

		side_panel_x = 50
		side_panel_y = 25
		side_panel_width = SCREEN_WIDTH * 0.2
		side_panel_height = SCREEN_HEIGHT * 0.9 + 10

		chatbox_x = side_panel_x + side_panel_width + 10
		chatbox_y = 25
		chatbox_width = SCREEN_WIDTH * 0.35
		chatbox_height = SCREEN_HEIGHT * 0.9 + 10

		turn_display_x = chatbox_x + chatbox_width + 10
		turn_display_y = 25
		turn_display_width = SCREEN_WIDTH * 0.35
		turn_display_height = SCREEN_HEIGHT * 0.30

		proposals_display_x = chatbox_x + chatbox_width + 10
		proposals_display_y = turn_display_y + turn_display_height + 10
		proposals_display_width = SCREEN_WIDTH * 0.35
		proposals_display_height = SCREEN_HEIGHT * 0.60

		self.sidepanel = PlayerSidepanel(
			players=engine.players,
			player_contributions=engine.player_contributions,
			x=side_panel_x,
			y=side_panel_y,
			width=side_panel_width,
			height=side_panel_height,
		)
		self.conversation_history = ConversationHistory(
			x=chatbox_x,
			y=chatbox_y,
			width=chatbox_width,
			height=chatbox_height,
		)

		self.turn_display = TurnDisplay(
			turn_display_x, turn_display_y, turn_display_width, turn_display_height
		)

		self.propsals = Proposals(
			proposals_display_x,
			proposals_display_y,
			proposals_display_width,
			proposals_display_height,
		)

		self.active_popup = None
		self.running = True
		self.simulation_finished = False
		self.leaderboard_popup = None

	def run(self):
		while self.running:
			self._handle_events()
			self._draw()
			pg.display.flip()

		pg.quit()
		sys.exit()

	def _handle_events(self):
		for event in pg.event.get():
			if event.type == pg.QUIT:
				self.running = False

			if self.leaderboard_popup:
				self.leaderboard_popup.handle_event(event)
				if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
					self.leaderboard_popup = None
				continue

			if self.active_popup:
				self.active_popup.handle_event(event)
				if (
					event.type == pg.MOUSEBUTTONDOWN
					and event.button == 1
					and not self.active_popup.rect.collidepoint(event.pos)
				):
					self.active_popup = None
				continue

			clicked_player = self.sidepanel.handle_event(event)
			if clicked_player:
				popup_width = SCREEN_WIDTH * 0.75
				popup_height = SCREEN_HEIGHT * 0.75

				popup_x = (SCREEN_WIDTH - popup_width) / 2
				popup_y = (SCREEN_HEIGHT - popup_height) / 2

				self.active_popup = PlayerPopup(
					player=clicked_player,
					x=popup_x,
					y=popup_y,
					width=popup_width,
					height=popup_height,
				)
			else:
				self.conversation_history.handle_event(event)
				self.propsals.handle_event(event)

			if (
				not self.simulation_finished
				and event.type == pg.KEYDOWN
				and event.key == pg.K_SPACE
			):
				turn_result = self.engine.step()

				if turn_result is None or turn_result.get('is_over'):
					self.simulation_finished = True
					score_data = self.engine.final_scores()
					lb_width = SCREEN_WIDTH * 0.7
					lb_height = SCREEN_HEIGHT * 0.75
					lb_x = (SCREEN_WIDTH - lb_width) / 2
					lb_y = (SCREEN_HEIGHT - lb_height) / 2
					self.leaderboard_popup = Leaderboard(
						score_data, self.engine.player_names, lb_x, lb_y, lb_width, lb_height
					)

				self.sidepanel.update_contributions(self.engine.player_contributions)
				self.turn_display.update_info(turn_result)
				self.propsals.update_info(turn_result, self.engine.player_names)
				self.conversation_history.add_message(turn_result)

	def _draw(self):
		self.screen.fill(WHITE)

		self.sidepanel.update()
		self.sidepanel.draw(self.screen)
		self.turn_display.draw(self.screen)
		self.propsals.draw(self.screen)
		self.conversation_history.draw(self.screen)

		if self.active_popup:
			self.active_popup.draw(self.screen)

		if self.leaderboard_popup:
			self.leaderboard_popup.draw(self.screen)
