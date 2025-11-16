import numpy as np
from sqlalchemy.orm import Session
from models import AIModel, User
from datetime import datetime

class SaaSQLearningAgent:
    def __init__(self, model: AIModel):
        self.model = model
        self.q_table = model.get_q_table()
        self.learning_rate = model.learning_rate
        self.discount_factor = model.discount_factor
        self.epsilon = model.epsilon
    
    def get_state_key(self, state):
        if isinstance(state, (list, tuple)):
            return str(tuple(state))
        return str(state)
    
    def predict_action(self, state) -> int:
        state_key = self.get_state_key(state)
        
        if state_key not in self.q_table:
            self.q_table[state_key] = [0.0, 0.0, 0.0, 0.0]
        
        if np.random.random() < self.epsilon:
            return np.random.randint(0, len(self.q_table[state_key]))
        
        return int(np.argmax(self.q_table[state_key]))
    
    def update_model(self, state, action: int, reward: float, next_state, db: Session):
        state_key = self.get_state_key(state)
        next_state_key = self.get_state_key(next_state)
        
        if state_key not in self.q_table:
            self.q_table[state_key] = [0.0, 0.0, 0.0, 0.0]
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = [0.0, 0.0, 0.0, 0.0]
        
        current_q = self.q_table[state_key][action]
        max_next_q = max(self.q_table[next_state_key])
        
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_table[state_key][action] = new_q
        
        # Save to database
        self.model.set_q_table(self.q_table)
        self.model.updated_at = datetime.utcnow()
        db.commit()
    
    def get_status(self):
        return {
            "model_id": self.model.id,
            "model_name": self.model.name,
            "q_table": self.q_table,
            "total_states": len(self.q_table),
            "learning_rate": self.learning_rate,
            "discount_factor": self.discount_factor,
            "epsilon": self.epsilon,
            "last_updated": self.model.updated_at.isoformat()
        }