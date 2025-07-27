TutiSecure: Yüz Tanıma Tabanlı Kimlik Doğrulama Sistemi

Merhaba!
Ben Simge. Bu proje Acunmedya Akademi’deki bitirme projem olarak geliştirdiğim, yüz tanıma temelli güvenli kimlik doğrulama sistemidir.

Bu projeyi geliştirirken hem teknik hem de kişisel olarak çok şey öğrendim. Karşıma çıkan her hatada bir adım daha ileri gittim. Umarım siz de hem fikirden hem de emekten keyif alırsınız.

Proje Hakkında
SMGSecure, kullanıcıların yüzlerini kullanarak sisteme güvenli bir şekilde giriş yapmasını sağlayan bir kimlik doğrulama sistemidir.
Python tabanlı Flask web framework, MongoDB veritabanı, TensorFlow, MediaPipe ve FaceNet gibi teknolojilerle geliştirildi. 
Docker desteği sayesinde kurulumu ve çalıştırılması oldukça kolaydır.

Temel Özellikler
Fonksiyonel Özellikler:

Kullanıcı yüz verisi kaydı (Face Enrollment)

10’dan fazla poz ile kayıt desteği

Gerçek zamanlı yüz algılama

Yüz eşleştirme ve yüzde benzerlik hesaplama

%70 eşik değeri altında giriş reddi

128 boyutlu embedding ile veri saklama

Hatalı giriş loglama (IP ve zaman damgası ile)

Admin paneli ile kullanıcı ve log yönetimi

Sadece admin yetkilisi yeni kullanıcı ekleyebilir

Aynı anda birden fazla yüz varsa işlem iptal edilir

Teknik Özellikler:

FaceNet modeliyle yüz embedding çıkarımı

MongoDB ile veritabanı bağlantısı

Flask + Jinja2 + JavaScript ile kullanıcı arayüzü

JWT ile API güvenliği

Docker ile kolay kurulum

Tailwind CSS ile frontend stilleri

Kurulum ve Çalıştırma
Gereksinimler:

Docker Desktop

Git

Adımlar:

Projeyi klonlayın:
git clone https://github.com/kullaniciadi/SMGSecure.git
cd SMGSecure

.env dosyasını oluşturun ve şu bilgileri ekleyin:
SECRET_KEY='gizli-bir-key'
MONGO_URI=mongodb://admin:password@mongodb:27017/
DATABASE_NAME='smgsecure_db'
ADMIN_USERNAME='simge'
ADMIN_PASSWORD='127598simge'
JWT_SECRET_KEY='daha-da-gizli-bir-key'
FLASK_PORT=5000

Uygulamayı çalıştırın:
DOCKER_DEFAULT_PLATFORM=linux/arm64 docker compose up --build -d

Uygulamaya erişmek için tarayıcıdan http://localhost:5001 adresine gidin.

Giriş Testi
Login sayfasında ADMIN_USERNAME ve ADMIN_PASSWORD ile giriş yaparak sistemi test edebilirsiniz. Dashboard'a erişebilir, yeni kullanıcı kaydı yapabilir ve yüz tanıma sürecini deneyebilirsiniz.

Karşılaştığım Sorunlar ve Çözümleri

.env dosyası okunamadı → python-dotenv kurularak çözüldü

Docker volume hatası → Docker Desktop ayarlarında paylaşım izni verildi

Port meşgul hatası → Tüm container’lar durdurulup silindi

OpenCV libGL.so.1 hatası → Dockerfile’a gerekli sistem kütüphaneleri eklendi

pip timeout hatası → timeout ve retry argümanları eklendi

TensorFlow eksik hatası → requirements.txt güncellendi

Boş görüntü hatası → Kodda kontrol yapıları ile hata yönetimi sağlandı

Token eksik hatası → HTML sayfalarda dekoratörler kaldırıldı, sadece API’da koruma sağlandı

Embedding çıkarma hatası → try-except ve log sistemi geliştirildi

Sonraki Geliştirme Adımları

Kullanıcı profil yönetimi

Parola sıfırlama özelliği

Canlı yüz algılama sırasında görsel geri bildirim

Detaylı kullanıcı rol sistemi

Embedding’lerin şifrelenmesi

CI/CD entegrasyonu ile otomatik test ve dağıtım


Simge Sargın
simge.sargn@gmail.com
LinkedIn: https://www.linkedin.com/in/simgesarg%C4%B1n-9812s/

Bu proje tamamen bireysel çabamla hazırlanmıştır.
