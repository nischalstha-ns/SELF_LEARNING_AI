from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class FileMetadata(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer)

class ModelMetadata(Base):
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True)
    model_name = Column(String(255), nullable=False)
    model_type = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    accuracy = Column(String(50))

# Database setup
engine = create_engine("sqlite:///./ai_app.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)