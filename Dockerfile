FROM python:3.9-alpine

RUN pip install pipenv

RUN mkdir /app
WORKDIR /app

COPY Pipfile Pipfile.lock ./

RUN set -ex && pipenv install --deploy --system

RUN addgroup -S app && adduser -S -G app app
USER app

COPY . .

ENV SIGNAL_REST_URL \
    SENDER_NUMBER \
    SMTP_HOST \
    SMTP_USER \
    SMTP_PASSWORD \
    SMTP_PORT=587

EXPOSE 8025
ENTRYPOINT ["python", "-u", "app.py"]
