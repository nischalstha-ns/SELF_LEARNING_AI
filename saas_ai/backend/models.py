from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    subscription_tier = Column(String(50), default="free")  # free, pro, enterprise
    api_calls_used = Column(Integer, default=0)
    api_calls_limit = Column(Integer, default=100)  # free tier limit
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    ai_models = relationship("AIModel", back_populates="user")

class AIModel(Base):
    __tablename__ = "ai_models"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(255), nullable=False)
    model_type = Column(String(100), default="q_learning")
    q_table_data = Column(Text)  # JSON string
    learning_rate = Column(Float, default=0.1)
    discount_factor = Column(Float, default=0.95)
    epsilon = Column(Float, default=0.1)
    total_states = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="ai_models")
    
    def get_q_table(self):
        return json.loads(self.q_table_data) if self.q_table_data else {}
    
    def set_q_table(self, q_table):
        self.q_table_data = json.dumps(q_table)
        self.total_states = len(q_table)

class APIUsage(Base):
    __tablename__ = "api_usage"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    endpoint = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)
    response_time = Column(Float)
    success = Column(Boolean, default=True)