FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alcohol_screening_server.py .
COPY model.joblib .
COPY templates/ templates/

EXPOSE 10000


CMD ["python", "alcohol_screening_server.py"]