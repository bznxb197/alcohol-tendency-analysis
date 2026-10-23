FROM python:3.12-slim

# LightGBM требует OpenMP, которого нет в slim-образе
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY preprocessing.py alcohol_screening_server.py model.joblib model_config.json ./
COPY templates/ templates/

ENV PORT=10000
EXPOSE 10000

CMD ["python", "alcohol_screening_server.py"]
