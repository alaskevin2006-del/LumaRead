FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ARG DEBIAN_MIRROR=https://deb.debian.org/debian
RUN sed -i "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources && apt-get -o Acquire::Retries=2 -o Acquire::https::Timeout=30 update && apt-get -o Acquire::Retries=2 -o Acquire::https::Timeout=30 install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
RUN useradd -u 10001 -m luma && mkdir -p /data/media && chown -R luma:luma /data
USER luma
CMD ["uvicorn","app.main:create_app","--factory","--host","0.0.0.0","--port","8000","--proxy-headers","--forwarded-allow-ips","*"]
