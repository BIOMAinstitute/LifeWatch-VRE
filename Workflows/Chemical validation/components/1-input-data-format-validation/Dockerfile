FROM python:3.11-slim

WORKDIR /code

RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    numpy==1.26.4 \
    openpyxl==3.1.2

COPY data_format_validation.py .

ENTRYPOINT ["python", "data_format_validation.py"]