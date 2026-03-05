FROM python:3.13-slim

LABEL version="1.0"
LABEL description="Deployable MQTT Mesh Network"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY src .

ENTRYPOINT ["python", "service.py"]

