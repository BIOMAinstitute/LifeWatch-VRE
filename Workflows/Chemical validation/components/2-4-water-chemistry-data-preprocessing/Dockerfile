FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY run_pipeline.py ./
COPY scripts/ ./scripts/

ENTRYPOINT ["python", "/app/run_pipeline.py"]
