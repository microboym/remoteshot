FROM python:3.12-slim

RUN apt-get update && apt-get install -y python3-pip

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY server.py /app/server.py
COPY index.html /app/index.html

CMD ["python", "/app/server.py", "--logging", "debug"]
