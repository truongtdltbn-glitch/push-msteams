FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py config.py .env .
COPY services/ services/
COPY templates/ templates/
COPY static/ static/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/config', timeout=5)"

# Run Flask app
CMD ["python", "app.py"]
EXPOSE 5000
