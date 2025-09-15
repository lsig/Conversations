from models.player import Item, Player, PlayerSnapshot
from .utils import ConversationScorer

import heapq

class BayesianTreeNode():
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

    
class BayesianTree():
    def __init__(self, decay_rate=0.5, root_probability=1): ##
        self.decay_rate = decay_rate 
        self.size = 0
        self.root_probability = root_probability
        self.root = None

    def get_child_probability(self, node:BayesianTreeNode):
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
			father=father
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
 
        
class BayesianTreeBeamSearch():
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
            
        level = 0
        leaves = [start_node]
        context_stack = self.context_stack
        while level < self.depth:
            # traverse all nodes
            next_level_candidates = []
            for leaf in leaves:
                branch_nodes = self._tree_branch_to_list(leaf, start_node)
                # Ensure only non-None item memories are used in context
                branch_items = [n.memory for n in branch_nodes if n.memory is not None]
                context_stack.extend(branch_items)
                for item in items:
                    score = self.scorer.evaluate(item, context_stack)
                    new_node = tree.add_node(leaf, item, score)
                    next_level_candidates.append(new_node)
                # Add pause option (no item contributed on this branch)
                pause_node = tree.add_node(leaf, None, 0.0)
                next_level_candidates.append(pause_node)
                # context_stack = context_stack[:-level-1]
                # del context_stack[-len(branch_list):]
                if branch_items:
                    del context_stack[-len(branch_items):]
                
            # global selection
            leaves = self._find_top_nodes(next_level_candidates, start_node)
            
            # backward prunnning
            for node in next_level_candidates:
                if node not in leaves:
                    tree.leaf_branch_backward_prunning(node)

            level += 1
    
    def backward_get_best_candidate(self, node:BayesianTreeNode, root_for_score:BayesianTreeNode):
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
                best_node = child ## !!!
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
	def __init__(self, 
              snapshot: PlayerSnapshot, 
              conversation_length: int, 
              competition_rate: float = 0.5,
              depth=1,
              breadth=None,
              breadth_rate=None, 
              threhold = 0
              ) -> None:  
     
		super().__init__(snapshot, conversation_length)
		self.scorer = ConversationScorer(self.preferences, competition_rate)
		self.depth = depth
		
		if breadth is not None:
			self.breadth = breadth
		elif breadth_rate is not None:
			self.breadth = max(1, int(breadth_rate * len(self.memory_bank)))
		else:
			self.breadth = len(self.memory_bank) 
			
		self.threshold = threhold

	def propose_item(self, history: list[Item]) -> Item | None:
		# Search best item
		searcher = BayesianTreeBeamSearch(
			scorer=self.scorer,
			depth=self.depth,
			breadth=self.breadth,
			initial_context_stack=list(history)
		)
		best_item, score = searcher.search(self.memory_bank, decay_rate=0.5)

		# Current use the stadic threhold... No behaviour learning. 
		# if score > self.threhold:
		if score > self.threshold:
			return best_item 
		else:
			return None 

		

# update: allow stop in the search. 

# update: scoring ~ normalized by total probability

# Next: 1, dynamic threhold based on history (shared) + individual 
# 		2, threhold during searching? 
# 		3, change based on global parameters? P,B,S,L,T?
# 		4, Bahavior Modeling by score estimation (Sequence modeling + online learning)

