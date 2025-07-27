import cv2
import mediapipe as mp
import numpy as np
from keras_facenet import FaceNet 
from loguru import logger
import os

# FaceNet modeli
try:
    facenet_model = FaceNet() 
    logger.info("FaceNet modeli başarıyla yüklendi (keras-facenet).")
except Exception as e:
    logger.error(f"FaceNet modeli yüklenirken hata: {e}") 
    facenet_model = None

mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

# Yüz algılama için
DETECTION_CONFIDENCE = 0.70 
TRACKING_CONFIDENCE = 0.5 

def preprocess_face(image, required_size=(160, 160)):
    """
    Simge: Yüz görüntüsünü FaceNet modelinin beklediği formata getiriyor.
    Boyutlandırma ve standardizasyon burada yapılıyor.
    """
    # Görüntünün boş olup olmadığını kontrol et boşsa None döndür
    if image is None or image.size == 0 or image.shape[0] == 0 or image.shape[1] == 0: 
        logger.warning("preprocess_face: Görüntü boş veya geçersiz boyutlara sahip, None döndürüldü.")
        return None

    try:
        # yeniden boyutlandırdım
        resized_image = cv2.resize(image, required_size)
        resized_image = resized_image.astype('float32')
        
        mean, std = resized_image.mean(), resized_image.std()
        image_standardized = (resized_image - mean) / std 
        
       
        image_expanded = np.expand_dims(image_standardized, axis=0) 
        return image_expanded
    except Exception as e:
        logger.error(f"preprocess_face: Görüntü ön işleme sırasında hata: {e}")
        return None

def get_face_embedding(face_image):
    """
    Simge: Verilen yüz görüntüsünden 128 boyutlu benzersiz bir "yüz imzası" çıkarır.
    Bu imza, diğer yüzlerle karşılaştırmak için kullanılacak.
    """
    if facenet_model is None:
        logger.error("get_face_embedding: FaceNet modeli yüklenemedi. Embedding çıkarılamıyor.")
        return None
    
    
    on_islenmis_yuz = preprocess_face(face_image)
    if on_islenmis_yuz is None: 
        logger.warning("get_face_embedding: Ön işlenmiş yüz boş veya geçersiz, embedding çıkarılamıyor.")
        return None

    try:
        embedding = facenet_model.embeddings(on_islenmis_yuz)[0] 
        
      
        embedding_norm = embedding / np.linalg.norm(embedding) 
        return embedding_norm
    except Exception as e:
        logger.error(f"get_face_embedding: Embedding çıkarımı sırasında hata: {e}")
        return None

def detect_faces(frame):
    """
    Simge: Kamera görüntüsündeki yüzleri algılar ve her yüzün konumunu (bounding box) döndürür.
    MediaPipe'ın hızlı ve doğru yüz algılama yeteneğini kullanıyorum.
    """
    algilanan_yuzler = [] 
    
    # Görüntünün boş olup olmadığını kontrol et. BoşsaOpenCV hatası vermeden boş liste döndür.
    if frame is None or frame.size == 0 or frame.shape[0] == 0 or frame.shape[1] == 0: 
        logger.warning("detect_faces: Görüntü boş veya geçersiz, yüz algılanamadı.")
        return []

    try:
        h, w, _ = frame.shape 
        with mp_face_detection.FaceDetection(min_detection_confidence=DETECTION_CONFIDENCE) as face_detection:
            results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if results.detections:
                for detection in results.detections:
                    bboxC = detection.location_data.relative_bounding_box
                    ih, iw, _ = frame.shape
                    x, y, genislik, yukseklik = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                                             int(bboxC.width * iw), int(bboxC.height * ih)
                    algilanan_yuzler.append((x, y, genislik, yukseklik)) 
        return algilanan_yuzler
    except Exception as e:
        logger.error(f"detect_faces: Yüz algılama sırasında hata: {e}")
        return []

def calculate_similarity(embedding1, embedding2):
    """
    Simge: İki yüz imzası (embedding) arasındaki benzerliği kosinüs benzerliği ile hesaplar.
    Değer 0 ile 100 arasında olacak şekilde ölçekleniyor, bu daha anlaşılır.
    """
    if embedding1 is None or embedding2 is None:
        logger.warning("calculate_similarity: Benzerlik hesaplaması için eksik embedding. 0.0 döndürüldü.") 
        return 0.0 

    try:
        nokta_carpim = np.dot(embedding1, embedding2) 
        norm_embed1 = np.linalg.norm(embedding1)
        norm_embed2 = np.linalg.norm(embedding2)

        if norm_embed1 == 0 or norm_embed2 == 0:
            logger.warning("calculate_similarity: Sıfır normlu embedding bulundu, benzerlik 0.0 döndürüldü.") 
            return 0.0

        benzerlik_orani = nokta_carpim / (norm_embed1 * norm_embed2) 
        return ((benzerlik_orani + 1) / 2) * 100 
    except Exception as e:
        logger.error(f"calculate_similarity: Benzerlik hesaplama sırasında hata: {e}")
        return 0.0

def get_face_roi(frame, bbox):
    """
    Simge: Ana görüntüden sadece yüz bölgesini (Region of Interest) kırpar.
    Bu kırpılan bölge FaceNet modeline verilecek.
    """
    x, y, w, h = bbox
    
    
    if y < 0: y = 0
    if x < 0: x = 0
    if y + h > frame.shape[0]: h = frame.shape[0] - y
    if x + w > frame.shape[1]: w = frame.shape[1] - x

    if w <= 0 or h <= 0: 
        logger.warning(f"get_face_roi: Geçersiz kırpma boyutları (w={w}, h={h}), boş ROI döndürüldü.")
        return None

    try:
        yuz_bolgesi_resim = frame[y:y+h, x:x+w]
        return yuz_bolgesi_resim
    except Exception as e:
        logger.error(f"get_face_roi: Yüz bölgesi kırpma sırasında hata: {e}")
        return None

def draw_annotations(frame, faces):
    """
    Simge: Algılanan yüzlerin etrafına yeşil dikdörtgenler çizer.
    Bu, kullanıcının yüzünün algılanıp algılanmadığını görsel olarak görmesini sağlar.
    """
    if frame is None or frame.size == 0: #Boş frame kontrol
        return frame

    try:
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2) 
        return frame
    except Exception as e:
        logger.error(f"draw_annotations: Çerçeve çizimi sırasında hata: {e}")
        return frame