from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Union
from q_learning import QLearningAgent

app = FastAPI(title="Self-Learning AI API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Q-learning agent
agent = QLearningAgent()

class PredictRequest(BaseModel):
    state: Union[List[float], List[int], str]

class UpdateRequest(BaseModel):
    state: Union[List[float], List[int], str]
    action: int
    reward: float
    next_state: Union[List[float], List[int], str]

@app.get("/")
def root():
    return {"message": "Self-Learning AI API is running"}

@app.post("/predict")
def predict_action(request: PredictRequest):
    try:
        action = agent.predict_action(request.state)
        return {"action": action, "state": request.state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update")
def update_model(request: UpdateRequest):
    try:
        agent.update_model(
            request.state, 
            request.action, 
            request.reward, 
            request.next_state
        )
        return {"message": "Model updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
def get_status():
    try:
        return agent.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)