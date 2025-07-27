Proje Hakkında
TutiSecure, kullanıcıların yüzlerini kullanarak sisteme güvenli şekilde giriş yapmalarını sağlayan modern bir kimlik doğrulama çözümüdür.
Python tabanlı Flask web çerçevesi, MongoDB veritabanı ve güçlü makine öğrenimi kütüphaneleri (TensorFlow, MediaPipe, FaceNet) ile geliştirilmiştir.
Docker desteği sayesinde kolayca kurulabilir ve çalıştırılabilir.

## Özellikler ve Karşılanan İsterler
# Fonksiyonel İsterler
Kullanıcı Yüz Verisi Kaydı:
/register sayfasında yeni kullanıcılar yüz verilerini kaydedebilir.

Çoklu Poz Kaydı (10+ Farklı Poz):
Kullanıcı "Yüz Kaydet" butonuna bastıkça 10’dan fazla poz alınır. "Kullanıcıyı Kaydet" butonu, bu şart sağlandığında aktif olur.

Canlı Yüz Algılama:
Kamera akışı gerçek zamanlıdır. Yüzler algılandığında yeşil kutular çizilir.

Yüz Eşleştirme (% Benzerlik Oranı):
Kosinüs benzerliğiyle iki yüz embedding’i arasındaki benzerlik % olarak hesaplanır.

Eşik Değeriyle Giriş Reddi:
%70 altında kalan eşleşmeler reddedilir (config.py’de DETECTION_CONFIDENCE ayarlanmıştır).

Yüz Verilerinin Depolanması:
128 boyutlu embedding’ler MongoDB’de saklanır (kriptografik hash değil, doğrudan).

Hatalı Giriş Loglama:
Başarısız girişler kullanıcı adı, IP ve zaman damgası ile loglanır.

Admin Paneli ve Kullanıcı Yönetimi:
/admin panelinde kullanıcı listesi, silme ve hata logları görüntülenebilir.

Admin Yetkili Yeni Kullanıcı Ekleme:
Yeni kullanıcı kaydı sadece admin yetkisiyle yapılabilir.

Çoklu Yüz Algılama Uyarısı:
Kamerada birden fazla yüz algılanırsa işlem reddedilir.

# Teknik Gereksinimler
Face Embedding:
keras-facenet ile FaceNet modelinden 128 boyutlu yüz embedding’leri çıkarılır.

Veritabanı:
MongoDB kullanılır. docker-compose.yml ile servise bağlanır.

Kullanıcı Arayüzü:
Flask + Tailwind CSS ile oluşturulmuştur. Jinja2 template yapısı kullanılır.

API Güvenliği:
JWT ile tüm hassas endpoint'ler korunur.

Konteynerleştirme:
Dockerfile ve docker-compose ile yapılandırılmıştır.

(Opsiyonel) PCA ile boyut indirgeme henüz uygulanmamıştır.


## Karşılaşılan Engeller ve Çözümleri
Her sorun bir şey öğretti. İşte bazıları:

python-dotenv Eksikliği → requirements.txt dosyasına eklendi

Docker Volume Erişimi Reddi → Docker Desktop’da dosya paylaşımı açıldı

Port Çakışması (5001) → Tüm konteynerler temizlendi

OpenCV libGL Hatası → Dockerfile'a gerekli sistem kütüphaneleri eklendi

pip install Timeout → --timeout 300 --retries 5 parametreleri eklendi

TensorFlow Eksikliği → tensorflow paketi manuel olarak eklendi

cv2.resize Hatası → Boş görüntüler için kontroller eklendi

Token Eksikliği (HTML sayfaları) → @token_required dekoratörleri sadece API’lerde bırakıldı

## Gelecek Planlar

Yüz algılama sırasında anlık geri bildirimler

Parola sıfırlama mekanizması

Kullanıcı profil yönetimi

Daha detaylı kullanıcı rolleri

Embedding’ler için şifreli saklama

Performans optimizasyonları

CI/CD entegrasyonu

## İletişim
Simge Sargın
simge.sargn@gmail.com
LinkedIn: https://www.linkedin.com/in/simgesarg%C4%B1n-9812s/
