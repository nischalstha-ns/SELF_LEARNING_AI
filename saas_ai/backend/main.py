from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Union
import time
from models import Base, User, AIModel, APIUsage
from auth import get_current_user, verify_password, get_password_hash, create_access_token, check_api_limit, security
from ai_service import SaaSQLearningAgent

# Database setup
DATABASE_URL = "sqlite:///./saas_ai.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Learning SaaS", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class ModelCreate(BaseModel):
    name: str
    learning_rate: float = 0.1
    discount_factor: float = 0.95
    epsilon: float = 0.1

class PredictRequest(BaseModel):
    state: Union[List[float], List[int], str]
    model_id: int

class UpdateRequest(BaseModel):
    state: Union[List[float], List[int], str]
    action: int
    reward: float
    next_state: Union[List[float], List[int], str]
    model_id: int

# Auth endpoints
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    
    # Create default model
    default_model = AIModel(user_id=db_user.id, name="Default Model")
    db.add(default_model)
    db.commit()
    
    return {"message": "User registered successfully"}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Model management
@app.post("/models")
def create_model(model: ModelCreate, db: Session = Depends(get_db), current_user: User = Depends(lambda: get_current_user(db=get_db()))):
    db_model = AIModel(
        user_id=current_user.id,
        name=model.name,
        learning_rate=model.learning_rate,
        discount_factor=model.discount_factor,
        epsilon=model.epsilon
    )
    db.add(db_model)
    db.commit()
    return {"model_id": db_model.id, "message": "Model created"}

@app.get("/models")
def get_models(db: Session = Depends(get_db), current_user: User = Depends(lambda: get_current_user(db=get_db()))):
    models = db.query(AIModel).filter(AIModel.user_id == current_user.id).all()
    return [{"id": m.id, "name": m.name, "total_states": m.total_states, "created_at": m.created_at} for m in models]

# AI endpoints
@app.post("/predict")
def predict_action(request: PredictRequest, db: Session = Depends(get_db), current_user: User = Depends(lambda: get_current_user(db=get_db()))):
    start_time = time.time()
    
    check_api_limit(current_user)
    
    model = db.query(AIModel).filter(AIModel.id == request.model_id, AIModel.user_id == current_user.id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    agent = SaaSQLearningAgent(model)
    action = agent.predict_action(request.state)
    
    # Track usage
    current_user.api_calls_used += 1
    usage = APIUsage(user_id=current_user.id, endpoint="predict", response_time=time.time() - start_time)
    db.add(usage)
    db.commit()
    
    return {"action": action, "state": request.state, "model_id": request.model_id}

@app.post("/update")
def update_model(request: UpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(lambda: get_current_user(db=get_db()))):
    start_time = time.time()
    
    check_api_limit(current_user)
    
    model = db.query(AIModel).filter(AIModel.id == request.model_id, AIModel.user_id == current_user.id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    agent = SaaSQLearningAgent(model)
    agent.update_model(request.state, request.action, request.reward, request.next_state, db)
    
    # Track usage
    current_user.api_calls_used += 1
    usage = APIUsage(user_id=current_user.id, endpoint="update", response_time=time.time() - start_time)
    db.add(usage)
    db.commit()
    
    return {"message": "Model updated successfully"}

@app.get("/status/{model_id}")
def get_status(model_id: int, db: Session = Depends(get_db), current_user: User = Depends(lambda: get_current_user(db=get_db()))):
    model = db.query(AIModel).filter(AIModel.id == model_id, AIModel.user_id == current_user.id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    agent = SaaSQLearningAgent(model)
    return agent.get_status()

@app.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db), current_user: User = Depends(lambda: get_current_user(db=get_db()))):
    models = db.query(AIModel).filter(AIModel.user_id == current_user.id).all()
    return {
        "user": {
            "email": current_user.email,
            "subscription_tier": current_user.subscription_tier,
            "api_calls_used": current_user.api_calls_used,
            "api_calls_limit": current_user.api_calls_limit
        },
        "models": [{"id": m.id, "name": m.name, "total_states": m.total_states} for m in models]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)