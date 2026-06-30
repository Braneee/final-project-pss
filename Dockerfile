FROM python:3.11-slim

WORKDIR /code

COPY code/requirements.txt .
RUN pip install -r requirements.txt

COPY code/ .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
