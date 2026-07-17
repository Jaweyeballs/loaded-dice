# --- frontend ---
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- app ---
FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[web]"

COPY --from=web /web/dist ./web/dist

ENV LOADED_DICE_STATIC=/app/web/dist
ENV LOADED_DICE_RELOAD=0
ENV PORT=8000

EXPOSE 8000
CMD ["uvicorn", "loaded_dice.server:app", "--host", "0.0.0.0", "--port", "8000"]
