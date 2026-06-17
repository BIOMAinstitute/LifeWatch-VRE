FROM python:3.11-slim

RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    openpyxl==3.1.2

COPY data2final_report.py ./
ENTRYPOINT ["python", "./data2final_report.py"]
