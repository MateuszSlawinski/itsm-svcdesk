# ai-generated: 100% - updated the course template to upgrade OS packages and remove pip from the runtime image
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && pip uninstall -y pip

COPY src/ /app/src/
COPY fixtures/ /app/fixtures/

RUN mkdir -p /data
ENV SVCDESK_DB=/data/svcdesk.db

EXPOSE 8080
CMD ["uvicorn", "main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8080"]
