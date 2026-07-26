# Image de démonstration Renov.ia : un seul conteneur sert l'API et le front.
# Même origine en production, donc ni CORS ni URL d'API à configurer côté client.

# ---------- Étape 1 : compilation du front (React + TypeScript + Vite) ----------
FROM node:20-alpine AS front
WORKDIR /front

# package.json/lock d'abord : la couche npm est mise en cache tant que les
# dépendances ne bougent pas.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---------- Étape 2 : image d'exécution ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt

# Seulement ce qui sert à l'exécution : domaine, optimiseur, passerelle REST,
# jeux synthétiques par ville + scores pré-calculés. Le pipeline ml/ et le
# générateur restent hors image (exclus par .dockerignore).
COPY domain/ ./domain/
COPY optimizer/ ./optimizer/
COPY backend/ ./backend/
COPY data/synthetic/ ./data/synthetic/
COPY --from=front /front/dist ./frontend/dist

# Exécution sans privilèges root.
RUN useradd --create-home --uid 10001 renovia && chown -R renovia:renovia /app
USER renovia

EXPOSE 8000

# Render injecte $PORT ; 8000 sert de repli en local (docker run -p 8000:8000 ...).
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
