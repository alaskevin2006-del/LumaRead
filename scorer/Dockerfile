FROM python:3.12-slim
ARG DEBIAN_MIRROR=https://deb.debian.org/debian
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN sed -i "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources && apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir --no-deps torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt torch==2.8.0
COPY . .
ENV HF_HOME=/cache/huggingface NUMBA_CACHE_DIR=/cache/numba OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
RUN useradd -u 10001 -m scorer && mkdir /cache && chown scorer /cache
USER scorer
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
