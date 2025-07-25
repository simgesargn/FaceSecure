from pymongo import MongoClient
from config import Config
from loguru import logger
import bcrypt
import datetime
import jwt

# MongoDB bağlantısı
try:
    client = MongoClient(Config.MONGO_URI)
    db = client[Config.DATABASE_NAME]
    logger.info("MongoDB bağlantısı başarılı!")
except Exception as e:
    logger.error(f"MongoDB bağlantı hatası: {e}")
    db = None # Bağlantı hatası durumunda db'yi None olarak ayarla

class User:
    def __init__(self):
        # BURAYI DÜZELTTİK: db'nin None olup olmadığını açıkça kontrol et
        self.collection = db.users if db is not None else None 

    def create_user(self, username, password, face_embeddings):
        # BURAYI DÜZELTTİK: self.collection'ın None olup olmadığını açıkça kontrol et
        if self.collection is None: 
            logger.error("MongoDB bağlantısı yok, kullanıcı oluşturulamıyor.") 
            return None

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user_data = {
            "username": username,
            "password": hashed_password,
            "face_embeddings": face_embeddings, 
            "created_at": datetime.datetime.now(),
            "last_login": None
        }
        try:
            result = self.collection.insert_one(user_data)
            logger.info(f"Kullanıcı '{username}' başarıyla oluşturuldu. ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Kullanıcı oluşturulurken hata: {e}")
            return None

    def get_user_by_username(self, username):
        # BURAYI DÜZELTTİK
        if self.collection is None: return None
        return self.collection.find_one({"username": username})

    def get_user_by_id(self, user_id):
        from bson.objectid import ObjectId
        # BURAYI DÜZELTTİK
        if self.collection is None: return None
        try:
            return self.collection.find_one({"_id": ObjectId(user_id)})
        except Exception as e:
            logger.error(f"Kullanıcı ID ile getirilirken hata: {e}")
            return None

    def verify_password(self, stored_password_hash, provided_password):
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password_hash.encode('utf-8'))

    def update_last_login(self, user_id):
        from bson.objectid import ObjectId
        # BURAYI DÜZELTTİK
        if self.collection is None: return
        try:
            self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_login": datetime.datetime.now()}}
            )
        except Exception as e:
            logger.error(f"Son giriş zamanı güncellenirken hata: {e}")

    def delete_user(self, user_id):
        from bson.objectid import ObjectId
        # BURAYI DÜZELTTİK
        if self.collection is None: return False
        try:
            result = self.collection.delete_one({"_id": ObjectId(user_id)})
            if result.deleted_count == 1:
                logger.info(f"Kullanıcı ID {user_id} başarıyla silindi.")
                return True
            return False
        except Exception as e:
            logger.error(f"Kullanıcı silinirken hata: {e}")
            return False

class FailedLogin:
    def __init__(self):
        # BURAYI DÜZELTTİK: db'nin None olup olmadığını açıkça kontrol et
        self.collection = db.failed_logins if db is not None else None 

    def log_attempt(self, username, ip_address):
        # BURAYI DÜZELTTİK
        if self.collection is None: return
        log_data = {
            "username": username,
            "ip_address": ip_address,
            "timestamp": datetime.datetime.now()
        }
        try:
            self.collection.insert_one(log_data)
            logger.warning(f"Hatalı giriş denemesi: Kullanıcı '{username}', IP: {ip_address}")
        except Exception as e:
            logger.error(f"Hatalı giriş loglanırken hata: {e}")

def generate_token(user_id):
    payload = {
        'user_id': str(user_id), 
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24) 
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')

def decode_token(token):
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        logger.warning("Token süresi dolmuş!")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Geçersiz token!")
        return None
