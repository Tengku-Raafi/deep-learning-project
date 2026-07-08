FROM python:3.10-slim

# Library sistem yang dibutuhkan OpenCV & MediaPipe di image minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face Spaces expose port 7860 secara default
EXPOSE 7860
ENV PORT=7860

CMD ["python", "app.py"]