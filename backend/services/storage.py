import os
import uuid
from pathlib import Path

class StorageService:
    def __init__(self):
        self.storage_path = Path("uploads")
        self.storage_path.mkdir(exist_ok=True)
    
    async def upload(self, file):
        file_id = str(uuid.uuid4())
        file_path = self.storage_path / f"{file_id}_{file.filename}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return str(file_path)
    
    async def download(self, file_id):
        # Find file by ID
        for file_path in self.storage_path.glob(f"{file_id}_*"):
            with open(file_path, "rb") as f:
                return f.read()
        raise FileNotFoundError("File not found")