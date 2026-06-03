FROM python:3.11-slim

RUN pip install --no-cache-dir \
    pandas==2.2.2

COPY laboratory_loq_application.py ./
ENTRYPOINT ["python", "./laboratory_loq_application.py"]
