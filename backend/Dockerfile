FROM python:3.10

# Prevent interactive setup blocks during the build process
ENV DEBIAN_FRONTEND=noninteractive

# Update the system and install Tesseract Core first
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install the language packages. The "|| true" tells Render to keep going even if a mirror hiccups.
RUN apt-get update && apt-get install -y \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-tam \
    tesseract-ocr-ben || true \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
