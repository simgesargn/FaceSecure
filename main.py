from app import create_app
from app.models import User
from config import Config
import numpy as np
from loguru import logger 
import os # os modülünü import etmeyi unutmayalım

# Uygulama objesini oluştur
app = create_app()

# İlk isteği almadan önce çalışacak fonksiyon
@app.before_first_request
def create_admin_user_if_not_exists():
    with app.app_context(): # Flask uygulama bağlamı içinde çalıştır
        user_model = User()
        # Admin kullanıcısının olup olmadığını kontrol et
        if user_model.get_user_by_username(Config.ADMIN_USERNAME) is None:
            # Simge: Admin için rastgele bir embedding oluşturuyorum,
            # çünkü ilk başta yüz verisi olmayacak.
            # Bu, uygulamanın sorunsuz başlamasını sağlıyor.
            dummy_embedding = np.random.rand(128).tolist() # 128 boyutlu rastgele bir embedding
            # Admin kullanıcısını oluştur
            user_model.create_user(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD, [dummy_embedding])
            logger.info(f"Varsayılan admin kullanıcısı '{Config.ADMIN_USERNAME}' başarıyla oluşturuldu.")
        else:
            logger.info("Admin kullanıcısı zaten mevcut.")
    
    # Simge: Uygulamanın temel başlangıç ayarlarının tamamlandığını loglayalım.
    logger.info("Uygulama başlangıç ön-işlemleri tamamlandı.")


# Uygulamayı sadece dosya doğrudan çalıştırıldığında başlat
if __name__ == '__main__':
    # Simge: Flask'ın kendi geliştirme sunucusu bazen Docker'da naz yapabiliyor.
    # Bu yüzden daha sağlam bir WSGI sunucusu olan Waitress'i deniyorum.
    # Umarım bu sefer sorunsuz başlar!
    try:
        from waitress import serve
        logger.info(f"Waitress sunucusu başlatılıyor. Dinlenen port: {Config.FLASK_PORT}") # Log ekledim
        serve(app, host="0.0.0.0", port=Config.FLASK_PORT)
    except ImportError:
        logger.warning("Waitress bulunamadı, Flask geliştirme sunucusu kullanılıyor. Üretim için Waitress'i kurmayı unutma!")
        app.run(debug=True, host='0.0.0.0', port=Config.FLASK_PORT) # Config'den portu alalım
    except Exception as e:
        logger.error(f"Uygulama başlatılırken beklenmedik bir hata oluştu: {e}") # Genel hata yakalama