FROM harbor.pgbank.com.vn/baseimage/python:3.11-slim

WORKDIR /app

COPY wheels /wheels
COPY requirements.txt .

RUN pip install \
    --no-index \
    --find-links=/wheels \
    -r requirements.txt

COPY app.py .
COPY config.py .
COPY services/ ./services/
COPY .env .

EXPOSE 8000
CMD ["python", "app.py"]
