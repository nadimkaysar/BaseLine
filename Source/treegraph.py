class GameTreeNode:
    def __init__(self, action, reward=0):
        self.action = action
        self.reward = reward
        self.children = []

    def add_child(self, child_node):
        self.children.append(child_node)

    def print_tree(self, level=0):
        print("  " * level + f"{self.action} (Reward: {self.reward:.2f})")
        for child in self.children:
            child.print_tree(level + 1)

class DBTGameTree:
    def __init__(self, actions):
        self.actions = actions  # Possible DBT actions
        self.root = GameTreeNode("Start")
        self.current_node = self.root  # Start from the root

    def expand_tree(self, reward_data):
        """Expand the tree from the previously selected best action based on reward data."""
        if not self.current_node.children:
            for action, reward in reward_data.items():
                self.current_node.add_child(GameTreeNode(action, reward))
        else:
            new_children = []
            for action, reward in reward_data.items():
                new_children.append(GameTreeNode(action, reward))
            self.current_node.children = new_children

    def select_best_action(self):
        """Select the action with the highest reward and expand from there."""
        if not self.current_node.children:
            return None, 0
        best_action_node = max(self.current_node.children, key=lambda x: x.reward)
        self.current_node = best_action_node  # Move to the best action node
        return best_action_node.action, best_action_node.reward

    def print_tree(self):
        """Print the entire game tree."""
        self.root.print_tree()


def data_extraction(data_dict):
    utility_scores = {}
    for key, values in list(data_dict['predictions'].items())[:-1]:
        utility_score = sum(float(state["probability"]) * float(state["reward"]) for state in values["possible_states"])
        utility_scores[key] = utility_score
    print("All Utility Scores:", utility_scores)
    return utility_scores


actions = ["Mindfulness", "Distress Tolerance", "Interpersonal Effectiveness", "Emotion Regulation"]
game_tree = DBTGameTree(actions)

def dataImport(reward_data):
    extracted_rewards = data_extraction(reward_data)
    game_tree.expand_tree(extracted_rewards)

    best_action, reward = game_tree.select_best_action()
    print(f"Best Action = {best_action}, Reward = {reward:.2f}")
    game_tree.expand_tree(extracted_rewards)

    # Print the final game tree
    game_tree.print_tree()
    return best_action
