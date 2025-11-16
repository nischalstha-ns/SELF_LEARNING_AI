from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import files, ai

app = FastAPI(title="Self Learning AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router, prefix="/api/files")
app.include_router(ai.router, prefix="/api/ai")

@app.get("/")
def root():
    return {"message": "Self Learning AI API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)