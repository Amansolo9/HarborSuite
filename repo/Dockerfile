FROM python:3.11-slim AS backend-base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace/fullstack

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY . .

FROM backend-base AS backend-runtime

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM node:20-alpine AS frontend-build

WORKDIR /workspace/fullstack/frontend
ENV VITE_API_BASE=http://localhost:8000

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM node:20-alpine AS frontend-runtime

WORKDIR /workspace/fullstack/frontend

COPY --from=frontend-build /workspace/fullstack/frontend/package*.json ./
COPY --from=frontend-build /workspace/fullstack/frontend/node_modules ./node_modules
COPY --from=frontend-build /workspace/fullstack/frontend/dist ./dist

EXPOSE 5173

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
