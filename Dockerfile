FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PORT=5000
EXPOSE 5000

CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
