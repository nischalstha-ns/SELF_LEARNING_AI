import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any

class QLearningAgent:
    def __init__(self, learning_rate=0.1, discount_factor=0.95, epsilon=0.1):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.q_table = {}
        self.data_path = Path("data/q_table.json")
        self.load_model()
    
    def get_state_key(self, state):
        """Convert state to string key for Q-table"""
        if isinstance(state, (list, tuple)):
            return str(tuple(state))
        return str(state)
    
    def predict_action(self, state) -> int:
        """Predict best action for given state"""
        state_key = self.get_state_key(state)
        
        if state_key not in self.q_table:
            # Initialize new state with random actions
            self.q_table[state_key] = [0.0, 0.0, 0.0, 0.0]  # 4 possible actions
        
        # Epsilon-greedy: explore vs exploit
        if np.random.random() < self.epsilon:
            return np.random.randint(0, len(self.q_table[state_key]))
        
        return int(np.argmax(self.q_table[state_key]))
    
    def update_model(self, state, action: int, reward: float, next_state):
        """Update Q-table based on experience"""
        state_key = self.get_state_key(state)
        next_state_key = self.get_state_key(next_state)
        
        # Initialize states if not exist
        if state_key not in self.q_table:
            self.q_table[state_key] = [0.0, 0.0, 0.0, 0.0]
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = [0.0, 0.0, 0.0, 0.0]
        
        # Q-learning update rule
        current_q = self.q_table[state_key][action]
        max_next_q = max(self.q_table[next_state_key])
        
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_table[state_key][action] = new_q
        self.save_model()
    
    def save_model(self):
        """Save Q-table to JSON file"""
        self.data_path.parent.mkdir(exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump(self.q_table, f, indent=2)
    
    def load_model(self):
        """Load Q-table from JSON file"""
        if self.data_path.exists():
            with open(self.data_path, 'r') as f:
                self.q_table = json.load(f)
    
    def get_status(self) -> Dict:
        """Return current model status"""
        return {
            "q_table": self.q_table,
            "total_states": len(self.q_table),
            "learning_rate": self.learning_rate,
            "discount_factor": self.discount_factor,
            "epsilon": self.epsilon
        }