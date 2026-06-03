FROM python:3.11-slim

RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    numpy==1.26.4 \
    openpyxl==3.1.2

COPY chemical_quality_validation.py ./
ENTRYPOINT ["python", "./chemical_quality_validation.py"]
