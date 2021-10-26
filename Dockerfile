FROM python:3.9.7-buster

WORKDIR /finder

COPY requirements.txt .

COPY init-db.sql /docker-entrypoint-initdb.d/

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "run.py"]