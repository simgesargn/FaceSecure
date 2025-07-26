import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    MONGO_URI = os.getenv('MONGO_URI')
    DATABASE_NAME = os.getenv('DATABASE_NAME')
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'access.log')
    
    # Simge: Yüz tanıma eşiği. Bu değeri %0 ile %1 arasında tutuyorum.
    # %0.70 demek %70 benzerlik ve üzeri kabul edilecek demek.
    # Bu noktada %70 benzerlik eşiği belirledim çünkü daha düşük değerlerde false positive (yanlış pozitif) çok artıyordu.
    # Yani, tanımadığım kişileri tanıyabiliyordu. Bu değeri kendi testlerime göre ayarladım.
    DETECTION_CONFIDENCE = 0.70 
    
    # Simge: Flask uygulamasının çalışacağı portu buraya ekledim.
    # Docker Compose'da 5001:5000 yapmıştık, yani konteyner içinde 5000'de çalışmalı.
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000)) # .env'den al, yoksa 5000 varsayılan olsun
