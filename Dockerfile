FROM python:3

WORKDIR /workspace

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY mbta.py .

CMD ["python3", "mbta.py"]
