from app import create_app
from app.models import User
from config import Config
import numpy as np
from loguru import logger 

# Uygulama objesini oluştur
app = create_app()

# İlk isteği almadan önce çalışacak fonksiyon
@app.before_first_request
def create_admin_user_if_not_exists():
    with app.app_context(): # Flask uygulama bağlamı içinde çalıştır
        user_model = User()
        # Admin kullanıcısının olup olmadığını kontrol et
        if user_model.get_user_by_username(Config.ADMIN_USERNAME) is None:
            # Örnek bir embedding (gerçekte yüz kaydından gelmeli)
            dummy_embedding = np.random.rand(128).tolist() # 128 boyutlu rastgele bir embedding
            # Admin kullanıcısını oluştur
            user_model.create_user(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD, [dummy_embedding])
            logger.info(f"Varsayılan admin kullanıcısı '{Config.ADMIN_USERNAME}' başarıyla oluşturuldu.")
        else:
            logger.info("Admin kullanıcısı zaten mevcut.")

# Uygulamayı sadece dosya doğrudan çalıştırıldığında başlat
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)