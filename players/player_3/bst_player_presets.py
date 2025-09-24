import heapq

from models.player import GameContext, Item, Player, PlayerSnapshot

from .utils import ConversationScorer

DEFAULT_SPEAK_PANELTY = 0


class BayesianTreeNode:
	def __init__(self, prior_probability, memory, score, father=None):
		self.prior_probability = prior_probability
		self.memory = memory
		self.score = score
		self.father = father
		self.childs = []
		# self.max_post_expectation = None
		# self.best_child = None

	def is_leaf(self):
		return len(self.childs) == 0


class BayesianTree:
	def __init__(self, decay_rate=0.5, root_probability=1):  ##
		self.decay_rate = decay_rate
		self.size = 0
		self.root_probability = root_probability
		self.root = None

	def get_child_probability(self, node: BayesianTreeNode):
		return node.prior_probability * self.decay_rate

	def add_node(self, father=None, memory=None, score=None):
		if self.root is None:
			prior_probability = self.root_probability
		else:
			prior_probability = self.get_child_probability(father)

		node = BayesianTreeNode(
			prior_probability=prior_probability,
			memory=memory,
			score=score,
			# prior_expectation=father.prior_expectation + prior_probability * score,
			father=father,
		)
		if self.root is None:
			self.root = node
		else:
			father.childs.append(node)

		return node

	def remove_node(self, node):
		# Guard: do not remove root or parentless nodes
		if node is None or node.father is None:
			return
		if node in node.father.childs:
			node.father.childs.remove(node)
		node.father = None
		del node

	def leaf_branch_backward_prunning(self, node):
		# if not node.is_leaf():
		if node is None or not node.is_leaf():
			return None
		father = node.father
		self.remove_node(node)
		# Stop if we've reached the root or lost the parent
		if father is None:
			return None
		self.leaf_branch_backward_prunning(father)


class BayesianTreeBeamSearch:
	def __init__(self, scorer, depth, width=None, breadth=None, initial_context_stack=None):
		self.context_stack = initial_context_stack if initial_context_stack is not None else []
		self.scorer = scorer
		self.depth = depth
		# allow alias breadth for width
		self.width = breadth if breadth is not None else (width if width is not None else 1)
		# self.decay_rate = decay_rate
		# self.search_tree = BayesianTree(decay_rate)

	def _find_top_nodes(self, nodes, start_node):
		heap = []
		for node in nodes:
			score = self._compute_normalized_expectation(node, start_node)
			# Previously skipped pauses/root (no memory):
			# if node.memory is None:
			#     continue
			heap.append((score, id(node), node))
		heapq.heapify(heap)
		top_items = heapq.nlargest(self.width, heap)
		# top_nodes = [item[1] for item in top_items]
		top_nodes = [item[2] for item in top_items]
		return top_nodes

	def _tree_branch_to_list(self, end_node, tail_node):
		li = []
		node = end_node
		# while node.father != tail_node:
		while node is not None and node != tail_node:
			li.append(node)
			node = node.father
		return list(reversed(li))

	def _compute_normalized_expectation(self, end_node, tail_node):
		path_nodes = self._tree_branch_to_list(end_node, tail_node)
		weighted_sum = 0.0
		prob_sum = 0.0
		for node in path_nodes:
			if node.memory is None:
				continue
			if node.score is None:
				continue
			weighted_sum += node.prior_probability * node.score
			prob_sum += node.prior_probability
		if prob_sum == 0.0:
			return 0.0
		return weighted_sum / prob_sum

	def forward_construct_search_tree(self, items, tree: BayesianTree, start_node=None):
		if start_node is None:
			start_node = tree.root

		leaves = [start_node]
		context_stack = self.context_stack
		depth = 0

		while leaves and depth < self.depth:
			next_level_candidates = []
			for leaf in leaves:
				# Stop expanding once a pause has been chosen, preserving branch length
				if leaf.memory is None and leaf is not start_node:
					next_level_candidates.append(leaf)
					continue

				branch_nodes = self._tree_branch_to_list(leaf, start_node)
				branch_items = [n.memory for n in branch_nodes if n.memory is not None]
				context_stack.extend(branch_items)

				for item in items:
					score = self.scorer.evaluate(item, context_stack)
					next_level_candidates.append(tree.add_node(leaf, item, score))

				# Insert pause without trimming it in later iterations
				pause_node = tree.add_node(leaf, None, 0.0)
				next_level_candidates.append(pause_node)

				if branch_items:
					del context_stack[-len(branch_items) :]

			# Select top candidates; pause nodes stay if selected here
			leaves = self._find_top_nodes(next_level_candidates, start_node)

			# Remove dominated branches except explicitly retained pause leaves
			for node in next_level_candidates:
				if node not in leaves and node.memory is not None:
					tree.leaf_branch_backward_prunning(node)

			depth += 1

	def backward_get_best_candidate(self, node: BayesianTreeNode, root_for_score: BayesianTreeNode):
		# Recursive: pick the best scoring leaf in the subtree
		if node.is_leaf():
			score = self._compute_normalized_expectation(node, root_for_score)
			# return node, score
			return None, score
		best_node = None
		# best_score = float('-inf')
		best_score = self._compute_normalized_expectation(node, root_for_score)
		for child in node.childs:
			_, candidate_score = self.backward_get_best_candidate(child, root_for_score)
			if candidate_score > best_score:
				# best_node = candidate_node
				best_node = child  ## !!!
				best_score = candidate_score
		return best_node, best_score

	def search(self, items, decay_rate):
		search_tree = BayesianTree(decay_rate, root_probability=2)
		search_tree.add_node()
		self.forward_construct_search_tree(items, search_tree)
		best_candidate, score = self.backward_get_best_candidate(search_tree.root, search_tree.root)
		if best_candidate:
			return best_candidate.memory, score
		else:
			return None, 0


class BayesianTreeBeamSearchPlayer(Player):
	def __init__(
		self,
		snapshot: PlayerSnapshot,
		ctx: GameContext,
		depth=1,
		breadth=None,
		breadth_rate=None,
		initial_competition_rate: float = 0.5,
		initial_speak_panelty: float = DEFAULT_SPEAK_PANELTY,  ##
		static_threhold=None,
	) -> None:
		super().__init__(snapshot, ctx)
		self.scorer = ConversationScorer(self.preferences, initial_competition_rate)
		self.depth = depth
		self.initial_competition_rate = initial_competition_rate
		self.initial_speak_panelty = initial_speak_panelty
		self.static_threhold = static_threhold

		if breadth is not None:
			self.breadth = breadth
		elif breadth_rate is not None:
			self.breadth = max(1, int(breadth_rate * len(self.memory_bank)))
		else:
			self.breadth = len(self.memory_bank)

	# ---------------------------------------------------------------------------------------------------------------------------------------------------

	# question to think about:
	# use which information to adjust & how: L(conversation_length) ~ T | B ~ S ~ available items | history
	def set_competition_rate(self, history):
		return self.initial_competition_rate  # currently use the

	def set_speak_panelty(self, history):
		return self.initial_speak_panelty

	# ---------------------------------------------------------------------------------------------------------------------------------------------------
	# discount_rate 0.12 | static_baseline 0.45 | blend_factor .60 have worked the best when paired against itself (emanuel)
	# 0.10, 0.53, 0.10 seem to work better when paired with greedy bots
	def dynamic_threshold(
		self,
		history: list,
		discount_rate: float = 0.12,
		static_baseline: float = 0.45,
		blend_factor: float = 0.6,
		##
		threshold_upper_bound: float = 0.6,
	) -> float:
		"""
		Compute a dynamic threshold for proposing items.

		- uses a discounted moving average of item scores.
		- skips 'None' items (pauses).
		- blends with a static baseline for stability.
		"""

		ema = None
		# skips through paused items
		### upper bound of cauculation.

		MAX_CONTEXT_LENGTH = int(10 / discount_rate) if discount_rate else 100
		t = len(history)
		# for i, item in enumerate(history):
		for i in range(max(0, t - MAX_CONTEXT_LENGTH), t):
			item = history[i]
			if item is None:
				continue
			### efficiency issue: O(N^2) --> O(N)
			# context = [x for x in history[:i] if x is not None]
			# score = self.scorer.evaluate(item, context)
			score = self.scorer.evaluate_at_position(history, i)
			# get a moving average of the scores
			ema = score if ema is None else discount_rate * score + (1 - discount_rate) * ema

		# if history was all None / pause, fallback to static baseline
		if ema is None:
			ema = static_baseline

		# blend average with static baseline
		threshold = blend_factor * ema + (1 - blend_factor) * static_baseline
		# threshold = max(threshold, ema + self.initial_speak_panelty) ## worse
		### add upper bound
		threshold = min(threshold, threshold_upper_bound)

		return threshold

	# ---------------------------------------------------------------------------------------------------------------------------------------------------

	def propose_item(self, history: list[Item]) -> Item | None:
		# 1, set the hyperparameters
		competition_rate = self.set_competition_rate(history)  # with suitable parameters.
		self.scorer.set_competition_rate(competition_rate)

		# 2, Search best item with highest scores.
		searcher = BayesianTreeBeamSearch(
			scorer=self.scorer,
			depth=self.depth,
			breadth=self.breadth,
			initial_context_stack=list(history),
		)
		best_item, score = searcher.search(self.memory_bank, decay_rate=0.5)

		# 3, decide whether to propose
		# (1) get the threhold
		if self.static_threhold is not None:
			threhold = self.static_threhold
		else:
			# speak_panelty = self.set_speak_panelty(history)
			# DEFULT_DISCOUNT_RATE = 0.1
			# DEFULT_CONTEXT_LENGTH = 10
			# score_expectation = self.scorer.calculate_expected_score(
			# history, mode='discount_average'
			# )
			threhold = self.dynamic_threshold(history)

		# (2) propose or keep silient
		if score > threhold:
			return best_item
		else:
			return None


# update: allow stop in the search.

# update: scoring ~ normalized by total probability

# Next: 1, dynamic threhold based on history (shared) + individual
#       2, threhold during searching?
#       3, change based on global parameters? P,B,S,L,T?
#       4, Bahavior Modeling by score estimation (Sequence modeling + online learning)
