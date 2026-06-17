FROM python:3.11-slim

RUN pip install --no-cache-dir \
    pandas==2.2.2

COPY unit_transformation.py ./
ENTRYPOINT ["python", "./unit_transformation.py"]
