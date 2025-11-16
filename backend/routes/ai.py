from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ai_service import AIService

router = APIRouter()
ai_service = AIService()

class PredictionRequest(BaseModel):
    data: dict
    model_type: str = "default"

@router.post("/predict")
async def predict(request: PredictionRequest):
    try:
        result = await ai_service.predict(request.data, request.model_type)
        return {"prediction": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train")
async def train_model(data: dict):
    try:
        result = await ai_service.train(data)
        return {"status": "training_started", "job_id": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))