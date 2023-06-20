FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY uptime_agent.py tasks.py models.py utils.py statics.py /app/

ENV PYTHONPATH "${PYTHONPATH}:/app"