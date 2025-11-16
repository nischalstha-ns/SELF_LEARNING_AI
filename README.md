# Self Learning AI Web Application

A web-based self-learning AI platform with file management and prediction capabilities.

## Structure
```
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── routes/
│   │   ├── files.py         # Upload/download endpoints
│   │   └── ai.py            # AI prediction endpoints
│   ├── services/
│   │   ├── storage.py       # Cloud storage logic
│   │   ├── ai_service.py    # AI model interaction
│   ├── models/
│   │   └── database.py      # DB models for metadata
│   ├── utils/
│   │   └── cache.py         # Redis caching
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── docker-compose.yml       # For SaaS deployment
└── README.md
```

## Quick Start

### Local Development
1. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Run backend:
   ```bash
   python main.py
   ```

3. Open `frontend/index.html` in browser

### Docker Deployment
```bash
docker-compose up -d
```

## Features
- File upload/download
- AI predictions with caching
- Model training endpoints
- Web interface for interactions