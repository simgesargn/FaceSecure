from flask import Blueprint, render_template, request, jsonify, Response, redirect, url_for
from app.models import User, FailedLogin, generate_token, decode_token
from app.utils import detect_faces, get_face_embedding, calculate_similarity, get_face_roi, draw_annotations
from config import Config
from functools import wraps
from loguru import logger
import cv2
import numpy as np
import base64
import os
import time

main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__)

user_model = User()
failed_login_model = FailedLogin()

# Simge: Bu dekoratör, API endpoint'lerimizi güvende tutmak için var.
# Her API isteğinde geçerli bir JWT token'ı bekliyor.
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Simge: Token'ı Authorization başlığından 'Bearer <token>' formatında alıyorum.
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            logger.warning("Token eksik! Yetkisiz API erişim denemesi.")
            return jsonify({'message': 'Token eksik!'}), 401
        
        try:
            current_user_id = decode_token(token)
            if not current_user_id:
                logger.warning("Geçersiz veya süresi dolmuş token ile API erişim denemesi.")
                return jsonify({'message': 'Token geçersiz veya süresi dolmuş!'}), 401
            
            current_user = user_model.get_user_by_id(current_user_id)
            if not current_user:
                logger.warning(f"Token'daki kullanıcı ID ({current_user_id}) ile kullanıcı bulunamadı.")
                return jsonify({'message': 'Kullanıcı bulunamadı!'}), 401
        except Exception as e:
            logger.error(f"Token doğrulama hatası: {e}")
            return jsonify({'message': 'Yetkilendirme hatası!'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

# Simge: Bu dekoratör, sadece admin yetkisi olan kullanıcıların erişebileceği API'ler için.
# Güvenlik katmanımızı daha da güçlendiriyor.
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            logger.warning("Admin yetkisi için token eksik!")
            return jsonify({'message': 'Token eksik!'}), 401
        
        try:
            current_user_id = decode_token(token)
            if not current_user_id:
                logger.warning("Geçersiz veya süresi dolmuş token ile admin erişim denemesi.")
                return jsonify({'message': 'Token geçersiz veya süresi dolmuş!'}), 401
            
            current_user = user_model.get_user_by_id(current_user_id)
            if not current_user:
                logger.warning(f"Admin yetkisi kontrolü için kullanıcı ID ({current_user_id}) bulunamadı.")
                return jsonify({'message': 'Kullanıcı bulunamadı!'}), 401

            # Simge: Basit bir admin kontrolü yapıyorum. Gerçek projelerde daha detaylı rol tabanlı yetkilendirme olur.
            if current_user['username'] != Config.ADMIN_USERNAME:
                logger.warning(f"Yetkisiz admin erişim denemesi: Kullanıcı '{current_user['username']}'.")
                return jsonify({'message': 'Yönetici yetkisi gerekli!'}), 403

        except Exception as e:
            logger.error(f"Admin yetki doğrulama hatası: {e}")
            return jsonify({'message': 'Yetkilendirme hatası!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated


# --- Ana Sayfa ve Kullanıcı Arayüzü Rotaları ---
# Simge: Bu sayfalar herkesin erişimine açık olmalı, o yüzden dekoratör kullanmıyorum.
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/register')
def register_page():
    return render_template('register.html')

@main_bp.route('/login')
def login_page():
    return render_template('login.html')

# Simge: Dashboard ve Admin sayfaları için token_required dekoratörünü kaldırdım.
# Çünkü bu sayfaların kendisi render edilirken henüz token olmayabilir.
# Token kontrolünü artık bu sayfaların içindeki JavaScript'te yapıyorum ve
# API çağrılarına ekliyorum, bu daha esnek bir yaklaşım.
@main_bp.route('/dashboard')
def dashboard_page():
    # Simge: Kullanıcı adını doğrudan template'e göndermiyorum, JS'ten alacak.
    return render_template('dashboard.html')

@main_bp.route('/admin')
def admin_page():
    # Simge: Admin panelindeki kullanıcı listesini doğrudan burada çekmiyorum,
    # JavaScript API çağrısı ile çekecek. Bu sayede sayfa daha hızlı yüklenir.
    return render_template('admin.html')

# --- Kimlik Doğrulama API Rotaları ---

@auth_bp.route('/register', methods=['POST'])
@admin_required # Simge: Yeni kullanıcı ekleme sadece admin yetkisiyle yapılmalı, güvenlik için kritik.
def register(current_user):
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    face_embeddings = data.get('face_embeddings') # 128 boyutlu embedding listesi

    if not username or not password or not face_embeddings:
        logger.warning("Kullanıcı kaydı için eksik bilgi alındı.")
        return jsonify({'message': 'Kullanıcı adı, parola ve yüz verileri gerekli!'}), 400

    if user_model.get_user_by_username(username):
        logger.warning(f"Kullanıcı adı '{username}' zaten mevcut, kayıt başarısız.")
        return jsonify({'message': 'Bu kullanıcı adı zaten mevcut.'}), 409

    if not isinstance(face_embeddings, list) or len(face_embeddings) == 0:
        logger.error("Geçersiz yüz verisi formatı alındı.")
        return jsonify({'message': 'Geçersiz yüz verisi formatı.'}), 400

    # Simge: Embedding'leri doğrudan veritabanına kaydediyorum.
    # Güvenlik için, hassas veritabanlarında embedding'ler şifrelenebilir.
    # Şimdilik hash'leme yapmıyorum çünkü hash'lenen embedding'ler karşılaştırılamaz.
    # Bu yüzden şimdilik doğrudan kaydediyorum.
    face_embeddings_np = [np.array(e, dtype=np.float32).tolist() for e in face_embeddings]

    user_id = user_model.create_user(username, password, face_embeddings_np)
    if user_id:
        logger.info(f"Yeni kullanıcı '{username}' başarıyla kaydedildi.")
        return jsonify({'message': 'Kullanıcı başarıyla kaydedildi!', 'user_id': user_id}), 201
    logger.error(f"Kullanıcı '{username}' kaydedilirken sunucu hatası oluştu.")
    return jsonify({'message': 'Kullanıcı kaydedilirken bir hata oluştu.'}), 500

@auth_bp.route('/login/password', methods=['POST'])
def login_with_password():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    ip_address = request.remote_addr # Simge: Kim nereden giriş yapmaya çalışıyor, loglamak önemli.

    if not username or not password:
        failed_login_model.log_attempt(username, ip_address)
        return jsonify({'message': 'Kullanıcı adı ve parola gerekli!'}), 400

    user = user_model.get_user_by_username(username)
    if user and user_model.verify_password(user['password'], password):
        token = generate_token(user['_id'])
        user_model.update_last_login(user['_id'])
        logger.info(f"Kullanıcı '{username}' parola ile başarıyla giriş yaptı. IP: {ip_address}")
        return jsonify({'message': 'Giriş başarılı!', 'token': token, 'username': user['username']}), 200
    else:
        failed_login_model.log_attempt(username, ip_address)
        logger.warning(f"Kullanıcı '{username}' parola ile giriş yapamadı. IP: {ip_address}")
        return jsonify({'message': 'Geçersiz kullanıcı adı veya parola.'}), 401

@auth_bp.route('/login/face', methods=['POST'])
def login_with_face():
    data = request.get_json()
    image_data = data.get('image')
    username_hint = data.get('username_hint') # Simge: Bu ipucu, büyük veri tabanlarında aramayı hızlandırabilir.
    ip_address = request.remote_addr

    if not image_data:
        failed_login_model.log_attempt("UNKNOWN", ip_address)
        return jsonify({'message': 'Görüntü verisi gerekli!'}), 400

    try:
        # Base64'ten görüntüyü çöz
        encoded_data = image_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            logger.warning(f"login_with_face: Geçersiz görüntü formatı veya boş kare. IP: {ip_address}") # Simge: Log ekledim.
            failed_login_model.log_attempt("UNKNOWN", ip_address)
            return jsonify({'message': 'Geçersiz görüntü formatı!'}), 400

        yuzler = detect_faces(frame) # Simge: Fonksiyon adını Türkçe bıraktım, daha samimi olsun.

        if len(yuzler) == 0:
            failed_login_model.log_attempt("UNKNOWN", ip_address)
            logger.warning(f"Yüz algılanmadı. Giriş reddedildi. IP: {ip_address}") 
            return jsonify({'message': 'Yüz algılanmadı.'}), 400
        elif len(yuzler) > 1:
            failed_login_model.log_attempt("UNKNOWN", ip_address)
            logger.warning(f"Birden fazla yüz algılandı. Giriş reddedildi. IP: {ip_address}")
            return jsonify({'message': 'Birden fazla yüz algılandı. Lütfen sadece bir yüzünüzün ekranda olduğundan emin olun.'}), 400

        # Algılanan tek yüzü işle
        (x, y, w, h) = yuzler[0]
        yuz_bolgesi = get_face_roi(frame, (x, y, w, h)) 
        
        if yuz_bolgesi is None: # Simge: Kırpılan yüz bölgesi boş gelirse hata ver.
            logger.warning(f"login_with_face: Yüz bölgesi kırpma sonrası boş. IP: {ip_address}")
            failed_login_model.log_attempt("UNKNOWN", ip_address)
            return jsonify({'message': 'Yüz bölgesi işlenirken hata.'}), 500

        anlik_yuz_embedding = get_face_embedding(yuz_bolgesi) 

        if anlik_yuz_embedding is None:
            failed_login_model.log_attempt("UNKNOWN", ip_address)
            logger.error(f"Yüz özellik çıkarımında hata. IP: {ip_address}")
            return jsonify({'message': 'Yüz özellik çıkarımında hata.'}), 500

        # Tüm kayıtlı kullanıcıları gez ve benzerlik kontrolü yap
        eslesen_kullanicilar = [] 
        if username_hint:
            kullanici = user_model.get_user_by_username(username_hint) 
            if kullanici: eslesen_kullanicilar.append(kullanici)
        else:
            if user_model.collection:
                eslesen_kullanicilar = list(user_model.collection.find({}))

        en_iyi_eslesen_kullanici = None 
        en_yuksek_benzerlik = Config.DETECTION_CONFIDENCE * 100 

        for kullanici_verisi in eslesen_kullanicilar: 
            for kaydedilmis_embedding_listesi in kullanici_verisi.get('face_embeddings', []): 
                kaydedilmis_embedding = np.array(kaydedilmis_embedding_listesi, dtype=np.float32) 
                benzerlik_orani = calculate_similarity(anlik_yuz_embedding, kaydedilmis_embedding) 
                if benzerlik_orani > en_yuksek_benzerlik:
                    en_yuksek_benzerlik = benzerlik_orani
                    en_iyi_eslesen_kullanici = kullanici_verisi
                    
        if en_iyi_eslesen_kullanici:
            token = generate_token(en_iyi_eslesen_kullanici['_id'])
            user_model.update_last_login(en_iyi_eslesen_kullanici['_id'])
            logger.info(f"Kullanıcı '{en_iyi_eslesen_kullanici['username']}' yüz ile başarıyla giriş yaptı. Benzerlik: {en_yuksek_benzerlik:.2f}%. IP: {ip_address}")
            return jsonify({
                'message': 'Giriş başarılı!',
                'token': token,
                'username': en_iyi_eslesen_kullanici['username'],
                'similarity': round(en_yuksek_benzerlik, 2)
            }), 200
        else:
            failed_login_model.log_attempt(username_hint or "UNKNOWN", ip_address)
            logger.warning(f"Yüz tanıma ile giriş başarısız. IP: {ip_address}. En yüksek benzerlik: {en_yuksek_benzerlik:.2f}%")
            return jsonify({'message': f'Yüz eşleşmesi bulunamadı. Benzerlik eşiği %{Config.DETECTION_CONFIDENCE*100} altında kaldı.'}), 401

    except Exception as e:
        logger.error(f"Yüzle giriş sırasında beklenmedik bir hata oluştu: {e}. IP: {ip_address}") 
        failed_login_model.log_attempt("UNKNOWN", ip_address)
        return jsonify({'message': 'Sunucu hatası.'}), 500

# Simge: Yeni endpoint! Bu, register sayfasının yüz embedding'lerini çekmek için kullanacağı yer.
# Sadece embedding çıkaracak, giriş yapmayacak.
@main_bp.route('/api/utils/extract_embedding', methods=['POST'])
def extract_embedding_api():
    data = request.get_json()
    image_data = data.get('image')
    ip_address = request.remote_addr

    if not image_data:
        logger.warning(f"Embedding çıkarımı için görüntü verisi eksik. IP: {ip_address}")
        return jsonify({'message': 'Görüntü verisi gerekli!'}), 400

    try:
        encoded_data = image_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            logger.warning(f"extract_embedding_api: Geçersiz görüntü formatı veya boş kare. IP: {ip_address}") # Simge: Log ekledim.
            return jsonify({'message': 'Geçersiz görüntü formatı!'}), 400

        yuzler = detect_faces(frame)

        if len(yuzler) == 0:
            logger.warning(f"Embedding çıkarımı için yüz algılanmadı. IP: {ip_address}")
            return jsonify({'message': 'Yüz algılanmadı.'}), 400
        elif len(yuzler) > 1:
            logger.warning(f"Embedding çıkarımı için birden fazla yüz algılandı. IP: {ip_address}")
            return jsonify({'message': 'Birden fazla yüz algılandı. Lütfen sadece bir yüzünüzün ekranda olduğundan emin olun.'}), 400

        (x, y, w, h) = yuzler[0]
        yuz_bolgesi = get_face_roi(frame, (x, y, w, h))
        
        if yuz_bolgesi is None: # Simge: Kırpılan yüz bölgesi boş gelirse hata ver.
            logger.warning(f"extract_embedding_api: Yüz bölgesi kırpma sonrası boş. IP: {ip_address}")
            return jsonify({'message': 'Yüz bölgesi işlenirken hata.'}), 500

        anlik_yuz_embedding = get_face_embedding(yuz_bolgesi)

        if anlik_yuz_embedding is None:
            logger.error(f"Embedding çıkarımında hata. IP: {ip_address}")
            return jsonify({'message': 'Yüz özellik çıkarımında hata.'}), 500

        logger.info(f"Yüz embedding'i başarıyla çıkarıldı. IP: {ip_address}")
        return jsonify({'embedding': anlik_yuz_embedding.tolist()}), 200 # Embedding'i liste olarak döndürüyoruz.

    except Exception as e:
        logger.error(f"Embedding çıkarımı sırasında beklenmedik bir hata oluştu: {e}. IP: {ip_address}")
        return jsonify({'message': 'Sunucu hatası.'}), 500


# --- Yönetim Paneli API Rotaları ---

@admin_bp.route('/users', methods=['GET'])
@token_required # Simge: Admin paneli kullanıcı listesi için token gerekli.
@admin_required # Simge: Sadece adminler bu listeyi görebilmeli.
def get_users(current_user):
    users = []
    if user_model.collection:
        # Simge: MongoDB'den tüm kullanıcıları çekiyorum. Password hash'lerini göndermemek güvenlik için önemli.
        for user in user_model.collection.find({}, {"username": 1, "created_at": 1, "last_login": 1}): 
            users.append({
                'id': str(user['_id']),
                'username': user['username'],
                'created_at': user['created_at'].isoformat() if 'created_at' in user else 'N/A',
                'last_login': user['last_login'].isoformat() if 'last_login' in user and user['last_login'] else 'N/A'
            })
    logger.info(f"Admin '{current_user['username']}' kullanıcı listesini görüntüledi.")
    return jsonify(users), 200

@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@token_required # Simge: Kullanıcı silme için token gerekli.
@admin_required # Simge: Sadece adminler kullanıcı silebilir.
def delete_user_api(current_user, user_id): # Fonksiyon adını değiştirdim, çakışmasın.
    if user_model.delete_user(user_id):
        logger.info(f"Admin '{current_user['username']}' kullanıcı ID '{user_id}' silindi.")
        return jsonify({'message': 'Kullanıcı başarıyla silindi.'}), 200
    logger.warning(f"Admin '{current_user['username']}' kullanıcı ID '{user_id}' silme denemesi başarısız oldu (bulunamadı?).")
    return jsonify({'message': 'Kullanıcı silinirken hata oluştu veya kullanıcı bulunamadı.'}), 404

@admin_bp.route('/failed_logins', methods=['GET'])
@token_required # Simge: Hatalı giriş logları için token gerekli.
@admin_required # Simge: Sadece adminler hatalı giriş loglarını görebilmeli.
def get_failed_logins(current_user):
    failed_attempts = []
    if failed_login_model.collection:
        # Simge: En son denemeler üstte görünsün diye zaman damgasına göre tersten sıralıyorum.
        for attempt in failed_login_model.collection.find({}).sort("timestamp", -1): 
            failed_attempts.append({
                'username': attempt['username'],
                'ip_address': attempt['ip_address'],
                'timestamp': attempt['timestamp'].isoformat()
            })
    logger.info(f"Admin '{current_user['username']}' hatalı giriş loglarını görüntüledi.")
    return jsonify(failed_attempts), 200


# Simge: Bu video akışı rotası, kameradan canlı görüntüyü web sayfasına aktarıyor.
# Yüz algılama ve çizimler burada frame frame işleniyor.
@main_bp.route('/video_feed')
def video_feed():
    def generate_frames():
        cap = cv2.VideoCapture(0) # 0 varsayılan kamera demek, benim bilgisayarımda bu çalışıyor.
        if not cap.isOpened():
            logger.error("Kamera açılamadı! Lütfen kamera bağlantısını veya izinleri kontrol edin.")
            # Simge: Kamera açılmazsa döngüye girmesin diye buradan çıkıyorum.
            return

        while True:
            success, frame = cap.read()
            if not success:
                logger.error("Kamera karesi okunamadı! Belki kamera bağlantısı kesildi?")
                break # Kare okunamıyorsa döngüyü kır.
            else:
                yuzler = detect_faces(frame) #Yüzleri algıla
                # Algılanan yüzlerin etrafına kutular çizmek için
                frame = draw_annotations(frame, yuzler) 

                # Görüntüyü JPEG formatına kodlayıp byte'a çeviriyorum.
            
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
            # Çok hızlı frame göndermemek için küçük bir gecikme ekledim,
           
            time.sleep(0.01) 

        cap.release()

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')