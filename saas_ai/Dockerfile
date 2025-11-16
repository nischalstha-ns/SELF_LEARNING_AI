FROM python:3.9-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000

ENV SECRET_KEY=your-production-secret-key-change-this
ENV DATABASE_URL=sqlite:///./saas_ai.db

CMD ["python", "main.py"]