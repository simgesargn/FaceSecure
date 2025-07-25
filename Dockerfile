# Python tabanlı bir base imajı kullan
FROM python:3.9-slim-bullseye

# Çalışma dizinini ayarla
WORKDIR /app

# Sistemsel bağımlılıkları yükle (OpenCV için gerekli)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libgtk2.0-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libgl1-mesa-glx \ 
    libsm6 \          
    libxext6 \       
    libxrender1 \     
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --timeout 300 --retries 5 -r requirements.txt

# Tüm uygulama dosyalarını kopyala
COPY . .

# Flask uygulamasını çalıştır
CMD ["python", "main.py"]
