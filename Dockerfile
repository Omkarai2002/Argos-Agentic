FROM python:3.14

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m nltk.downloader brown

CMD ["python", "-m", "sockets.client"]