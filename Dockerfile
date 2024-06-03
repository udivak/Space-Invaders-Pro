FROM python:latest

WORKDIR /app

COPY . /app

RUN pip install pygame

CMD ["python", "main.py"]