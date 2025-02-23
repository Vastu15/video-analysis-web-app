FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV PORT=10000

CMD gunicorn --bind 0.0.0.0:$PORT app:app