from core.engine import Engine
from ui.game import Game


def run_gui(engine: Engine):
	game = Game(engine)
	game.run()
