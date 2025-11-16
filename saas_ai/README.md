# AI Learning SaaS Platform

A complete Software-as-a-Service platform for self-learning AI with user authentication, subscription management, and multi-tenant AI model hosting.

## 🚀 Features

### **SaaS Features**
- **User Authentication**: JWT-based secure login/register
- **Multi-tenant**: Each user has isolated AI models
- **API Rate Limiting**: Usage tracking and limits per subscription tier
- **Subscription Tiers**: Free (100 calls), Pro (1000 calls), Enterprise (unlimited)
- **Dashboard**: Real-time usage statistics and model management

### **AI Capabilities**
- **Q-Learning Algorithm**: Advanced reinforcement learning
- **Model Management**: Create, manage multiple AI models per user
- **Persistent Storage**: Database-backed model persistence
- **Real-time Updates**: Live Q-table visualization
- **State Flexibility**: Support for array and string states

### **Production Ready**
- **Docker Deployment**: Complete containerization
- **Database**: SQLAlchemy with SQLite/PostgreSQL support
- **Security**: Password hashing, JWT tokens, CORS protection
- **Monitoring**: API usage tracking and analytics
- **Scalable**: Nginx reverse proxy, horizontal scaling ready

## 📁 File Structure
```
saas_ai/
├── backend/
│   ├── main.py              # FastAPI SaaS application
│   ├── models.py            # Database models (User, AIModel, APIUsage)
│   ├── auth.py              # Authentication & authorization
│   ├── ai_service.py        # Multi-tenant AI service
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html          # SaaS web interface
│   ├── app.js              # Frontend SaaS logic
│   └── style.css           # Professional styling
├── config/
│   └── nginx.conf          # Production web server config
├── Dockerfile              # Backend containerization
├── docker-compose.yml      # Full stack deployment
└── README.md
```

## 🏃‍♂️ Quick Start

### **Local Development**
```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Start backend
python main.py
# API: http://localhost:8000
# Docs: http://localhost:8000/docs

# 3. Open frontend
# Open frontend/index.html in browser
```

### **Production Deployment**
```bash
# Deploy with Docker
docker-compose up -d

# Access:
# Frontend: http://localhost
# Backend API: http://localhost/api
```

## 🔐 User Journey

### **1. Registration & Login**
- Register with email/password
- Secure JWT authentication
- Automatic default model creation

### **2. Dashboard Overview**
- API usage statistics
- Subscription tier information
- Model management interface

### **3. AI Model Management**
- Create multiple AI models
- Configure learning parameters
- Track model performance

### **4. AI Operations**
- Select active model
- Make predictions
- Train with feedback
- View Q-table evolution

## 📊 API Endpoints

### **Authentication**
- `POST /register` - User registration
- `POST /login` - User authentication

### **Model Management**
- `POST /models` - Create new AI model
- `GET /models` - List user's models

### **AI Operations**
- `POST /predict` - Get action prediction
- `POST /update` - Train model with experience
- `GET /status/{model_id}` - Get model status

### **Dashboard**
- `GET /dashboard` - User dashboard data

## 💰 Subscription Tiers

| Tier | API Calls/Month | Models | Price |
|------|----------------|--------|-------|
| Free | 100 | 3 | $0 |
| Pro | 1,000 | 10 | $29 |
| Enterprise | Unlimited | Unlimited | $99 |

## 🔧 Configuration

### **Environment Variables**
```bash
SECRET_KEY=your-jwt-secret-key
DATABASE_URL=sqlite:///./saas_ai.db
# For PostgreSQL: postgresql://user:pass@host:port/db
```

### **Database Migration**
```bash
# Auto-creates tables on first run
# For production, use Alembic migrations
```

## 🌐 Cloud Deployment

### **Heroku**
```bash
# 1. Create Procfile
echo "web: cd backend && python main.py" > Procfile

# 2. Deploy
git push heroku main
```

### **AWS/GCP/Azure**
```bash
# Use Docker image
docker build -t ai-saas .
# Deploy to container service
```

### **Domain Setup**
```bash
# Update frontend/app.js
const API_BASE = 'https://your-domain.com/api';
```

## 🧪 Testing

### **Manual Testing**
1. Register new user
2. Create AI model
3. Make predictions
4. Train with feedback
5. Monitor usage limits

### **API Testing**
```bash
# Test with curl
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

## 🔒 Security Features

- **Password Hashing**: Bcrypt encryption
- **JWT Tokens**: Secure session management
- **Rate Limiting**: API abuse prevention
- **Input Validation**: Pydantic models
- **CORS Protection**: Cross-origin security

## 📈 Scaling Considerations

- **Database**: Migrate to PostgreSQL for production
- **Caching**: Add Redis for session storage
- **Load Balancing**: Multiple backend instances
- **CDN**: Static asset delivery
- **Monitoring**: Add logging and metrics

## 🎯 Business Model

- **Freemium**: Free tier with upgrade path
- **Usage-based**: Pay per API call
- **Feature-gated**: Advanced features for paid tiers
- **White-label**: Custom branding options

This is a complete, production-ready SaaS platform that can be deployed immediately and scaled to serve thousands of users with their own AI models.