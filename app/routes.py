from flask import Blueprint, render_template, request, jsonify, Response, session, redirect, url_for
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

# JWT doğrulama dekoratörü
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return jsonify({'message': 'Token eksik!'}), 401
        try:
            current_user_id = decode_token(token)
            if not current_user_id:
                return jsonify({'message': 'Token geçersiz veya süresi dolmuş!'}), 401
            current_user = user_model.get_user_by_id(current_user_id)
            if not current_user:
                return jsonify({'message': 'Kullanıcı bulunamadı!'}), 401
        except Exception as e:
            logger.error(f"Token doğrulama hatası: {e}")
            return jsonify({'message': 'Token doğrulanamadı!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# Basit kontrol
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return jsonify({'message': 'Token eksik!'}), 401
        try:
            current_user_id = decode_token(token)
            if not current_user_id:
                return jsonify({'message': 'Token geçersiz veya süresi dolmuş!'}), 401
            current_user = user_model.get_user_by_id(current_user_id)
            if not current_user:
                return jsonify({'message': 'Kullanıcı bulunamadı!'}), 401

            # Basit admin kontrolü: Kullanıcı adı 'admin' ise admin yetkisi var sayalım
            if current_user['username'] != Config.ADMIN_USERNAME:
                return jsonify({'message': 'Yönetici yetkisi gerekli!'}), 403

        except Exception as e:
            logger.error(f"Admin yetki doğrulama hatası: {e}")
            return jsonify({'message': 'Yetkilendirme hatası!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated


# --- Ana Sayfa ve Kullanıcı Arayüzü Rotası ---
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/register')
def register_page():
    return render_template('register.html')

@main_bp.route('/login')
def login_page():
    return render_template('login.html')

@main_bp.route('/dashboard')
@token_required
def dashboard_page(current_user):
    return render_template('dashboard.html', username=current_user['username'])

@main_bp.route('/admin')
@admin_required
def admin_page(current_user):
    users = []
    if user_model.collection:
        users = list(user_model.collection.find({}, {"username": 1})) # Sadece kullanıcı adlarını al
    return render_template('admin.html', users=users)

# --- Kimlik Doğrulama API Rotaları ---

@auth_bp.route('/register', methods=['POST'])
@admin_required # Sadece admin yeni kullanıcı ekleyebilir
def register(current_user):
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    face_embeddings = data.get('face_embeddings') # List of 128-dim embeddings

    if not username or not password or not face_embeddings:
        return jsonify({'message': 'Kullanıcı adı, parola ve yüz verileri gerekli!'}), 400

    if user_model.get_user_by_username(username):
        return jsonify({'message': 'Bu kullanıcı adı zaten mevcut.'}), 409

    if not isinstance(face_embeddings, list) or len(face_embeddings) == 0:
        return jsonify({'message': 'Geçersiz yüz verisi formatı.'}), 400

    # Embeddings'leri numpy array'e çevir
    face_embeddings_np = [np.array(e, dtype=np.float32).tolist() for e in face_embeddings]

    user_id = user_model.create_user(username, password, face_embeddings_np)
    if user_id:
        return jsonify({'message': 'Kullanıcı başarıyla kaydedildi!', 'user_id': user_id}), 201
    return jsonify({'message': 'Kullanıcı kaydedilirken bir hata oluştu.'}), 500

@auth_bp.route('/login/password', methods=['POST'])
def login_with_password():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    ip_address = request.remote_addr

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
    username_hint = data.get('username_hint') # İsteğe bağlı, performansı artırabilir
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
            failed_login_model.log_attempt("UNKNOWN", ip_address)
            return jsonify({'message': 'Geçersiz görüntü formatı!'}), 400

        faces = detect_faces(frame)

        if len(faces) == 0:
            failed_login_model.log_attempt("UNKNOWN", ip_address)
            return jsonify({'message': 'Yüz algılanmadı.'}), 400
        elif len(faces) > 1:
            failed_login_model.log_attempt("UNKNOWN", ip_address)
            logger.warning(f"Birden fazla yüz algılandı. Giriş reddedildi. IP: {ip_address}")
            return jsonify({'message': 'Birden fazla yüz algılandı. Lütfen sadece bir yüzünüzün ekranda olduğundan emin olun.'}), 400

        # Algılanan tek yüzü işle
        (x, y, w, h) = faces[0]
        face_roi = get_face_roi(frame, (x, y, w, h))
        current_face_embedding = get_face_embedding(face_roi)

        if current_face_embedding is None:
            failed_login_model.log_attempt("UNKNOWN", ip_address)
            return jsonify({'message': 'Yüz özellik çıkarımında hata.'}), 500

        # Tüm kayıtlı kullanıcıları gez ve benzerlik kontrolü yap
        users_found = []
        if username_hint:
            user = user_model.get_user_by_username(username_hint)
            if user: users_found.append(user)
        else:
            if user_model.collection:
                users_found = list(user_model.collection.find({}))

        best_match_user = None
        highest_similarity = Config.DETECTION_CONFIDENCE * 100 # Eşik değeri

        for user_data in users_found:
            for stored_embedding_list in user_data.get('face_embeddings', []):
                stored_embedding = np.array(stored_embedding_list, dtype=np.float32)
                similarity = calculate_similarity(current_face_embedding, stored_embedding)
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match_user = user_data
                    
        if best_match_user:
            token = generate_token(best_match_user['_id'])
            user_model.update_last_login(best_match_user['_id'])
            logger.info(f"Kullanıcı '{best_match_user['username']}' yüz ile başarıyla giriş yaptı. Benzerlik: {highest_similarity:.2f}%. IP: {ip_address}")
            return jsonify({
                'message': 'Giriş başarılı!',
                'token': token,
                'username': best_match_user['username'],
                'similarity': round(highest_similarity, 2)
            }), 200
        else:
            failed_login_model.log_attempt(username_hint or "UNKNOWN", ip_address)
            logger.warning(f"Yüz tanıma ile giriş başarısız. IP: {ip_address}. En yüksek benzerlik: {highest_similarity:.2f}%")
            return jsonify({'message': f'Yüz eşleşmesi bulunamadı. Benzerlik eşiği %{Config.DETECTION_CONFIDENCE*100} altında kaldı.'}), 401

    except Exception as e:
        logger.error(f"Yüzle giriş sırasında hata: {e}")
        failed_login_model.log_attempt("UNKNOWN", ip_address)
        return jsonify({'message': 'Sunucu hatası.'}), 500

# --- Yönetim Paneli API Rotaları  ---

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users(current_user):
    users = []
    if user_model.collection:
        for user in user_model.collection.find({}):
            users.append({
                'id': str(user['_id']),
                'username': user['username'],
                'created_at': user['created_at'].isoformat() if 'created_at' in user else 'N/A',
                'last_login': user['last_login'].isoformat() if 'last_login' in user and user['last_login'] else 'N/A'
            })
    return jsonify(users), 200

@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(current_user, user_id):
    if user_model.delete_user(user_id):
        return jsonify({'message': 'Kullanıcı başarıyla silindi.'}), 200
    return jsonify({'message': 'Kullanıcı silinirken hata oluştu veya kullanıcı bulunamadı.'}), 404

@admin_bp.route('/failed_logins', methods=['GET'])
@admin_required
def get_failed_logins(current_user):
    failed_attempts = []
    if failed_login_model.collection:
        for attempt in failed_login_model.collection.find({}).sort("timestamp", -1):
            failed_attempts.append({
                'username': attempt['username'],
                'ip_address': attempt['ip_address'],
                'timestamp': attempt['timestamp'].isoformat()
            })
    return jsonify(failed_attempts), 200


@main_bp.route('/video_feed')
def video_feed():
    def generate_frames():
        cap = cv2.VideoCapture(0) # 0 for default camera
        if not cap.isOpened():
            logger.error("Kamera açılamadı!")
            return

        while True:
            success, frame = cap.read()
            if not success:
                logger.error("Kare okunamadı!")
                break
            else:
                faces = detect_faces(frame)
                frame = draw_annotations(frame, faces)

                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.01) # Daha akıcı akış için küçük bir gecikme

        cap.release()

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')