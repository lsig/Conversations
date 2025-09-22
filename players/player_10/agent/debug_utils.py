"""
Debug utilities for Player10 decision-making insights.

This module provides comprehensive debugging capabilities to understand
the agent's decision-making process at various levels of detail.
"""

from models.item import Item

from . import config as config_module


class DebugLogger:
	"""Centralized debug logging for Player10."""

	def __init__(self, player_id: str = 'P10'):
		self.player_id = player_id
		self.turn_count = 0
		self.enabled = config_module.DEBUG_ENABLED
		self.level = config_module.DEBUG_LEVEL

	def log(self, level: int, category: str, message: str, data: dict | None = None):
		"""Log a debug message with level and category filtering."""
		if not self.enabled or level > self.level:
			return

		prefix = f'[{self.player_id}:T{self.turn_count:02d}:{category}]'
		print(f'{prefix} {message}')

		if data and level >= 2:
			for key, value in data.items():
				print(f'    {key}: {value}')

	def log_strategy_selection(self, use_altruism: bool, random_value: float, threshold: float):
		"""Log strategy selection decision."""
		if not config_module.DEBUG_STRATEGY_SELECTION:
			return

		strategy = 'ALTRUISM' if use_altruism else 'ORIGINAL'
		self.log(
			1,
			'STRATEGY',
			f'Selected {strategy} strategy (r={random_value:.3f} {"<" if use_altruism else ">="} {threshold:.3f})',
		)

	def log_item_evaluation(
		self, item: Item, scores: dict[str, float], total_delta: float, rank: int
	):
		"""Log item evaluation and scoring."""
		if not config_module.DEBUG_ITEM_EVALUATION:
			return

		self.log(2, 'ITEM_EVAL', f"Item '{item.text[:30]}...' - Δ={total_delta:.3f} (rank {rank})")

		if self.level >= 2:
			self.log(
				2,
				'ITEM_EVAL',
				'Score breakdown:',
				{
					'importance': f'{scores.get("importance", 0):.3f}',
					'coherence': f'{scores.get("coherence", 0):.3f}',
					'freshness': f'{scores.get("freshness", 0):.3f}',
					'monotony': f'{scores.get("monotony", 0):.3f}',
				},
			)

	def log_altruism_gate(
		self, delta_self: float, expected_others: float, tau: float, decision: str, reason: str
	):
		"""Log altruism gate decision."""
		if not config_module.DEBUG_ALTRUISM_GATE:
			return

		self.log(
			2,
			'ALTRUISM_GATE',
			f'{decision}: Δ_self={delta_self:.3f} vs E[others]={expected_others:.3f} - τ={tau:.3f}',
		)
		self.log(2, 'ALTRUISM_GATE', f'Reason: {reason}')

	def log_performance_tracking(
		self, player_id: str, old_mean: float, new_mean: float, delta: float, count: int
	):
		"""Log performance tracking updates."""
		if not config_module.DEBUG_PERFORMANCE_TRACKING:
			return

		self.log(
			3,
			'PERF_TRACK',
			f'Updated {player_id}: μ={old_mean:.3f}→{new_mean:.3f} (Δ={delta:.3f}, n={count})',
		)

	def log_selection_forecast(self, weights: dict[str, float], expected_delta: float):
		"""Log selection forecasting."""
		if not config_module.DEBUG_SELECTION_FORECAST:
			return

		self.log(2, 'SEL_FORECAST', f'Expected Δ_others = {expected_delta:.3f}')

		if self.level >= 2:
			weight_str = ', '.join([f'{pid}:{w:.3f}' for pid, w in weights.items()])
			self.log(2, 'SEL_FORECAST', f'Weights: {weight_str}')

	def log_safety_check(self, check_type: str, condition: bool, action: str, reason: str):
		"""Log safety checks and failsafes."""
		if not config_module.DEBUG_SAFETY_CHECKS:
			return

		status = 'TRIGGERED' if condition else 'PASSED'
		self.log(1, 'SAFETY', f'{check_type} {status}: {action} - {reason}')

	def log_decision_summary(
		self, final_decision: Item | None, reason: str, strategy_used: str, confidence: float = 0.0
	):
		"""Log final decision summary."""
		if not self.enabled:
			return

		decision_text = f'Item(id={final_decision.id})' if final_decision else 'PASS'
		self.log(
			1, 'DECISION', f'Final: {decision_text} | Strategy: {strategy_used} | Reason: {reason}'
		)

		if confidence > 0:
			self.log(1, 'DECISION', f'Confidence: {confidence:.2f}')

	def start_turn(self, turn_number: int):
		"""Start a new turn for logging context."""
		self.turn_count = turn_number
		if self.enabled:
			print(f'\n{"=" * 60}')
			print(f'[{self.player_id}] TURN {turn_number:02d} - DECISION MAKING')
			print(f'{"=" * 60}')


def debug_item_ranking(items: list[Item], scores: list[float], max_items: int = 5) -> str:
	"""Create a debug string showing top items and their scores."""
	if not config_module.DEBUG_ENABLED or config_module.DEBUG_LEVEL < 2:
		return ''

	ranked_items = sorted(zip(items, scores, strict=False), key=lambda x: x[1], reverse=True)
	debug_str = '\n    Top items considered:\n'

	for i, (item, score) in enumerate(ranked_items[:max_items]):
		debug_str += f'    {i + 1}. Item(id={item.id}) (Δ={score:.3f})\n'

	return debug_str


def debug_performance_summary(tracker, player_id: str = 'P10') -> str:
	"""Create a debug string showing current performance tracking state."""
	if not config_module.DEBUG_ENABLED or config_module.DEBUG_LEVEL < 3:
		return ''

	global_mean = tracker.mu_global
	global_count = tracker.count_global
	player_means = tracker.mu_by_pid
	player_counts = tracker.count_by_pid

	debug_str = '\n    Performance tracking state:\n'
	debug_str += f'    Global: μ={global_mean:.3f} (n={global_count})\n'

	for pid, mean in player_means.items():
		count = player_counts.get(pid, 0)
		debug_str += f'    {pid}: μ={mean:.3f} (n={count})\n'

	return debug_str


def debug_conversation_context(history: list[Item], window: int = 5) -> str:
	"""Create a debug string showing recent conversation context."""
	if not config_module.DEBUG_ENABLED or config_module.DEBUG_LEVEL < 2:
		return ''

	recent_items = history[-window:] if len(history) >= window else history
	debug_str = f'\n    Recent conversation context (last {len(recent_items)} items):\n'

	for i, item in enumerate(recent_items):
		if item is None:
			debug_str += f'    {i + 1}. PAUSE\n'
		else:
			debug_str += f'    {i + 1}. Item(id={item.id})\n'

	return debug_str
