FROM python:3.12-slim
WORKDIR /app
COPY cloud/requirements.txt /app/cloud/requirements.txt
RUN pip install --no-cache-dir -r /app/cloud/requirements.txt
COPY cloud /app/cloud
EXPOSE 8080
CMD ["uvicorn", "cloud.main:app", "--host", "0.0.0.0", "--port", "8080"]
