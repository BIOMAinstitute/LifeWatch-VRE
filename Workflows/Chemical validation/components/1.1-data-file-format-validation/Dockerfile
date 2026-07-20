FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data_format_validation.py .

ENTRYPOINT ["python", "data_format_validation.py"]
