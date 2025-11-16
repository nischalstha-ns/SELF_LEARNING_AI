# Self-Learning AI System

A complete Q-learning based self-learning AI system with persistent storage and web interface.

## Features
- **Q-Learning Algorithm**: Reinforcement learning with epsilon-greedy exploration
- **Persistent Storage**: Q-table saved to `data/q_table.json`
- **REST API**: FastAPI backend with CORS enabled
- **Real-time UI**: Dynamic Q-table display and instant feedback
- **Responsive Design**: Works on desktop and mobile

## File Structure
```
ai_system/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── q_learning.py        # Q-learning implementation
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html          # Web interface
│   ├── app.js              # Frontend logic
│   └── style.css           # Styling
├── data/
│   └── q_table.json        # Persistent Q-table (auto-created)
├── Dockerfile              # Container build
├── docker-compose.yml      # Full deployment
└── README.md
```

## Quick Start

### Local Development
1. **Install Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Start Backend**:
   ```bash
   python main.py
   ```
   Server runs on http://localhost:8000

3. **Open Frontend**:
   Open `frontend/index.html` in browser

### Docker Deployment
```bash
docker-compose up -d
```
- Backend: http://localhost:8000
- Frontend: http://localhost

## API Endpoints

### POST /predict
Predict best action for given state.
```json
{
  "state": [1, 2, 3]
}
```
Response:
```json
{
  "action": 2,
  "state": [1, 2, 3]
}
```

### POST /update
Update model with experience.
```json
{
  "state": [1, 2, 3],
  "action": 2,
  "reward": 1.0,
  "next_state": [2, 3, 4]
}
```

### GET /status
Get current Q-table and model parameters.

## Usage Examples

1. **Simple State**: Enter `"start"` as state
2. **Array State**: Enter `[1, 2, 3]` as state
3. **Update**: Use action 0-3, any reward value

## How It Works

1. **Q-Learning**: Agent learns optimal actions through trial and error
2. **Epsilon-Greedy**: Balances exploration (random) vs exploitation (best known)
3. **Persistence**: Q-table automatically saves after each update
4. **Real-time**: Frontend updates Q-table display every 10 seconds

## Cloud Deployment

### Heroku
1. Create `Procfile`: `web: cd backend && python main.py`
2. Deploy backend folder
3. Serve frontend separately or use static hosting

### AWS/GCP
1. Use Docker image
2. Deploy with container service
3. Configure port 8000

The system is production-ready with proper error handling and CORS configuration.