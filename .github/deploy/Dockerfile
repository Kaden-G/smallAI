# deploy/Dockerfile
# Owner: @kaden
FROM python:3.10-slim


# best-effort system deps (add as needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
build-essential \
&& rm -rf /var/lib/apt/lists/*


WORKDIR /app


# Copy only requirements first for faster rebuilds
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


# Copy the rest of the project
COPY . .


# Ensure src is importable
ENV PYTHONPATH=/app/src


EXPOSE 8000


# Run the FastAPI server (deploy/serve.py)
CMD ["uvicorn", "deploy.serve:app", "--host", "0.0.0.0", "--port", "8000"]