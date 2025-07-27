from app import create_app
from app.models import User
from config import Config
import numpy as np
from loguru import logger 
import os 


# Uygulama objesini oluştur

app = create_app()


@app.before_first_request
def create_admin_user_if_not_exists():
    with app.app_context(): # Flask uygulama bağlamı içinde çalıştır
        user_model = User()
        # Admin kullanıcısının olup olmadığını kontrol et
        if user_model.get_user_by_username(Config.ADMIN_USERNAME) is None:
            

            # Bu, uygulamanın sorunsuz başlamasını sağlıyor.
            dummy_embedding = np.random.rand(128).tolist() # 128 boyutlu rastgele bir embedding
            # Admin kullanıcısını oluştur
            user_model.create_user(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD, [dummy_embedding])
            logger.info(f"Varsayılan admin kullanıcısı '{Config.ADMIN_USERNAME}' başarıyla oluşturuldu.")
        else:
            logger.info("Admin kullanıcısı zaten mevcut.")
    
  
    logger.info("Uygulama başlangıç ön-işlemleri tamamlandı.")



if __name__ == '__main__':

    try:
        from waitress import serve
        logger.info(f"Waitress sunucusu başlatılıyor. Dinlenen port: {Config.FLASK_PORT}") # Log ekledim
        serve(app, host="0.0.0.0", port=Config.FLASK_PORT)
    except ImportError:
        logger.warning("Waitress bulunamadı, Flask geliştirme sunucusu kullanılıyor. Üretim için Waitress'i kurmayı unutma!")
        app.run(debug=True, host='0.0.0.0', port=Config.FLASK_PORT) 
    except Exception as e:
        logger.error(f"Uygulama başlatılırken beklenmedik bir hata oluştu: {e}") # Genel hata yakalama