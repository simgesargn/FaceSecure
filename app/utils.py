import cv2
import mediapipe as mp
import numpy as np
from keras_facenet import FaceNet # Simge: FaceNet modelini bu kütüphane ile kolayca yükleyeceğiz.
# from sklearn.preprocessing import Normalizer # Simge: Bu modül, numpy/sklearn uyumsuzluğu yaptığı için şimdilik kaldırıldı.
from loguru import logger
import os

# Simge: FaceNet modelini başlatıyorum. keras_facenet kütüphanesi modeli otomatik indirip yönetiyor, harika!
try:
    facenet_model = FaceNet() 
    logger.info("FaceNet modeli başarıyla yüklendi (keras-facenet).")
except Exception as e:
    logger.error(f"FaceNet modeli yüklenirken hata: {e}") # Simge: Model yüklenmezse uygulama çalışmaz, o yüzden hata logu önemli.
    facenet_model = None

# MediaPipe Face Detection ve Face Mesh modüllerini başlatıyorum.
# Yüz algılama ve yüzdeki önemli noktaları bulmak için kullanılıyorlar.
mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

# Yüz algılama için eşik değerleri. Güven eşiği ne kadar yüksek olursa, algılama o kadar kesin olur.
DETECTION_CONFIDENCE = 0.8 # Simge: %80 güven eşiği belirledim, daha düşük değerlerde yanlış pozitifler artıyordu.
TRACKING_CONFIDENCE = 0.5 # MediaPipe Face Mesh'te tracking için de kullanılır, ama şimdilik sadece detection kullanıyoruz.

def preprocess_face(image, required_size=(160, 160)):
    """
    Simge: Yüz görüntüsünü FaceNet modelinin beklediği formata getiriyor.
    Boyutlandırma ve standardizasyon burada yapılıyor.
    """
    image = cv2.resize(image, required_size)
    image = image.astype('float32')
    mean, std = image.mean(), image.std()
    image = (image - mean) / std # Standardizasyon: Veriyi modele daha uygun hale getirir.
    image = np.expand_dims(image, axis=0) # Model tek bir resim yerine bir "batch" bekler, o yüzden boyut ekliyorum.
    return image

def get_face_embedding(face_image):
    """
    Simge: Verilen yüz görüntüsünden 128 boyutlu benzersiz bir "yüz imzası" çıkarır.
    Bu imza, diğer yüzlerle karşılaştırmak için kullanılacak.
    """
    if facenet_model is None:
        logger.error("FaceNet modeli yüklenemedi. Embedding çıkarılamıyor.")
        return None

    # Simge: Görüntüyü modele vermeden önce ön işleme tabi tutuyorum.
    on_islenmis_yuz = preprocess_face(face_image) 
    # Simge: Modelden embedding'i alıyorum.
    embedding = facenet_model.embeddings([on_islenmis_yuz])[0]
    
    # Simge: Normalizasyon işlemi, embedding'leri standart bir aralığa getirir,
    # bu da benzerlik hesaplamalarını daha güvenilir yapar.
    # Normalizer'ı kaldırdığımız için manuel normalizasyon yapıyorum.
    embedding_norm = embedding / np.linalg.norm(embedding) # L2 normalizasyon
    return embedding_norm

def detect_faces(frame):
    """
    Simge: Kamera görüntüsündeki yüzleri algılar ve her yüzün konumunu (bounding box) döndürür.
    MediaPipe'ın hızlı ve doğru yüz algılama yeteneğini kullanıyorum.
    """
    algilanan_yuzler = [] # Simge: Algılanan yüzleri bu listeye ekleyeceğim.
    h, w, _ = frame.shape # Görüntünün boyutlarını alıyorum.
    with mp_face_detection.FaceDetection(min_detection_confidence=DETECTION_CONFIDENCE) as face_detection:
        # Görüntüyü RGB'ye çevirmek MediaPipe için gerekli.
        results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if results.detections:
            for detection in results.detections:
                # Bounding box koordinatlarını alıyorum.
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                # Koordinatları piksel değerlerine çeviriyorum.
                x, y, genislik, yukseklik = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                                         int(bboxC.width * iw), int(bboxC.height * ih)
                algilanan_yuzler.append((x, y, genislik, yukseklik)) # Türkçe değişken adları
    return algilanan_yuzler

def calculate_similarity(embedding1, embedding2):
    """
    Simge: İki yüz imzası (embedding) arasındaki benzerliği kosinüs benzerliği ile hesaplar.
    Değer 0 ile 100 arasında olacak şekilde ölçekleniyor, bu daha anlaşılır.
    """
    if embedding1 is None or embedding2 is None:
        logger.warning("Benzerlik hesaplaması için eksik embedding. 0.0 döndürüldü.") # Simge: Log ekledim.
        return 0.0 

    # Kosinüs benzerliği formülü: (A . B) / (||A|| * ||B||)
    nokta_carpim = np.dot(embedding1, embedding2) # Simge: Türkçe değişken adı
    norm_embed1 = np.linalg.norm(embedding1)
    norm_embed2 = np.linalg.norm(embedding2)

    if norm_embed1 == 0 or norm_embed2 == 0:
        logger.warning("Sıfır normlu embedding bulundu, benzerlik 0.0 döndürüldü.") # Simge: Log ekledim.
        return 0.0

    benzerlik_orani = nokta_carpim / (norm_embed1 * norm_embed2) # Simge: Türkçe değişken adı
    # Kosinüs benzerliği -1 (tamamen zıt) ile 1 (tamamen aynı) arasındadır.
    # Benzerliği %0 ile %100 arasına ölçekliyorum, kullanıcı için daha anlamlı.
    return ((benzerlik_orani + 1) / 2) * 100 

def get_face_roi(frame, bbox):
    """
    Simge: Ana görüntüden sadece yüz bölgesini (Region of Interest) kırpar.
    Bu kırpılan bölge FaceNet modeline verilecek.
    """
    x, y, w, h = bbox
    
    # Simge: Yüz bölgesini çerçeveden kesiyorum.
    yuz_bolgesi_resim = frame[y:y+h, x:x+w]
    return yuz_bolgesi_resim

def draw_annotations(frame, faces):
    """
    Simge: Algılanan yüzlerin etrafına yeşil dikdörtgenler çizer.
    Bu, kullanıcının yüzünün algılanıp algılanmadığını görsel olarak görmesini sağlar.
    """
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2) # Yeşil renkli 2 piksel kalınlığında dikdörtgen.
    return frame