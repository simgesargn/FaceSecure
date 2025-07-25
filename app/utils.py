import cv2
import mediapipe as mp
import numpy as np
from keras_facenet import FaceNet
# from sklearn.preprocessing import Normalizer # Bu satırı tamamen silin
from loguru import logger
import os

# FaceNet modelini yükle (keras-facenet kütüphanesini kullanarak)
try:
    facenet_model = FaceNet()
    logger.info("FaceNet modeli başarıyla yüklendi (keras-facenet).")
except Exception as e:
    logger.error(f"FaceNet modeli yüklenirken hata: {e}")
    facenet_model = None

# MediaPipe Face Detection ve Face Mesh modüllerini başlat
mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

# Yüz algılama için eşik değerleri
DETECTION_CONFIDENCE = 0.8
TRACKING_CONFIDENCE = 0.5 

def preprocess_face(image, required_size=(160, 160)):
    image = cv2.resize(image, required_size)
    image = image.astype('float32')
    mean, std = image.mean(), image.std()
    image = (image - mean) / std
    image = np.expand_dims(image, axis=0)
    return image

def get_face_embedding(face_image):
    if facenet_model is None:
        logger.error("FaceNet modeli yüklenemedi. Embedding çıkarılamıyor.")
        return None

    preprocessed_face = preprocess_face(face_image) 
    embedding = facenet_model.embeddings([preprocessed_face])[0]
    # Normalizasyon satırlarını da kaldırıyoruz, çünkü Normalizer'ı kaldırdık.
    # Eğer normalize etmeniz gerekiyorsa, bunun için manuel bir numpy işlemi yazılabilir.
    return embedding

def detect_faces(frame):
    faces = []
    h, w, _ = frame.shape
    with mp_face_detection.FaceDetection(min_detection_confidence=DETECTION_CONFIDENCE) as face_detection:
        results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if results.detections:
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                             int(bboxC.width * iw), int(bboxC.height * ih)
                faces.append((x, y, w, h))
    return faces

def calculate_similarity(embedding1, embedding2):
    if embedding1 is None or embedding2 is None:
        return 0.0

    dot_product = np.dot(embedding1, embedding2)
    norm_embed1 = np.linalg.norm(embedding1)
    norm_embed2 = np.linalg.norm(embedding2)

    if norm_embed1 == 0 or norm_embed2 == 0:
        return 0.0

    similarity = dot_product / (norm_embed1 * norm_embed2)
    return ((similarity + 1) / 2) * 100

def get_face_roi(frame, bbox):
    x, y, w, h = bbox
    face_roi = frame[y:y+h, x:x+w]
    return face_roi

def draw_annotations(frame, faces):
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    return frame