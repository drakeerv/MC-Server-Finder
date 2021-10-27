FROM python:3.9.7-buster

WORKDIR /finder

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "run.py"]