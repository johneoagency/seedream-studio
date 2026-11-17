FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hosts (DigitalOcean, Render, etc.) inject the port to listen on via $PORT.
ENV PORT=3000
EXPOSE 3000

# gunicorn = production server. Long timeout so image polling isn't cut off.
CMD gunicorn --workers 2 --threads 4 --timeout 300 --bind 0.0.0.0:$PORT server:app
