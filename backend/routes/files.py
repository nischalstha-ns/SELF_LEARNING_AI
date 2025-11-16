from fastapi import APIRouter, UploadFile, File, HTTPException
from services.storage import StorageService
import json

router = APIRouter()
storage = StorageService()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_url = await storage.upload(file)
        return {"url": file_url, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{file_id}")
async def download_file(file_id: str):
    try:
        file_data = await storage.download(file_id)
        return file_data
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")