FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e . --extra-index-url https://pypi.org/simple/

COPY src/ src/

RUN mkdir -p models

CMD ["python", "-m", "plate_blurring.main"]
