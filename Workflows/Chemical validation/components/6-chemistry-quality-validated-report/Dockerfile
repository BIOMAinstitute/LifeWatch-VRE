FROM python:3.11-slim

RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    numpy==1.26.4 \
    matplotlib==3.9.0 \
    fpdf2==2.7.9 \
    openpyxl==3.1.2

COPY validation_report.py ./
ENTRYPOINT ["python", "./validation_report.py"]
