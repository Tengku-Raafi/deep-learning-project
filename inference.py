"""
inference.py - Modul deteksi isyarat realtime.
UI: minimal, hanya pojok kiri atas, font konsisten.

Versi browser-webcam: satu-satunya perubahan dari versi asli adalah
_get_cap()/release_kamera()/generate_frames() (yang membuka cv2.VideoCapture(0)
di server) diganti process_frame() yang menerima 1 frame dari browser lewat
HTTP. Semua logic deteksi, gambar landmark, dan panel info TIDAK diubah.
"""

import cv2
import numpy as np
import mediapipe as mp
import time
import base64

from tensorflow.keras.models import load_model

from config import MODEL_PATH, ACTIONS, SEQUENCE_LENGTH, CONFIDENCE_THRESHOLD, STABLE_FRAMES

mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

print("[inference] Modul browser-webcam (dengan panel kiri atas) dimuat")

model = None


def load_lstm_model():
    global model
    try:
        model = load_model(MODEL_PATH)
        print(f"[inference] Model loaded: {MODEL_PATH}")
        return True
    except Exception as e:
        print(f"[inference] Gagal load model: {e}")
        return False


_holistic = mp_holistic.Holistic(
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)


def mediapipe_detection(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False
    results = _holistic.process(image)
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    return image, results


def draw_landmarks(image, results):
    mp_drawing.draw_landmarks(
        image, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS,
        mp_drawing.DrawingSpec(color=(23, 160, 212), thickness=2, circle_radius=3),
        mp_drawing.DrawingSpec(color=(200, 200, 200), thickness=1, circle_radius=1)
    )
    mp_drawing.draw_landmarks(
        image, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS,
        mp_drawing.DrawingSpec(color=(23, 160, 212), thickness=2, circle_radius=3),
        mp_drawing.DrawingSpec(color=(200, 200, 200), thickness=1, circle_radius=1)
    )


def extract_keypoints(results):
    pose = np.array([[r.x, r.y, r.z, r.visibility]
                      for r in results.pose_landmarks.landmark]).flatten() \
        if results.pose_landmarks else np.zeros(33 * 4)
    lh = np.array([[r.x, r.y, r.z]
                    for r in results.left_hand_landmarks.landmark]).flatten() \
        if results.left_hand_landmarks else np.zeros(21 * 3)
    rh = np.array([[r.x, r.y, r.z]
                    for r in results.right_hand_landmarks.landmark]).flatten() \
        if results.right_hand_landmarks else np.zeros(21 * 3)
    return np.concatenate([pose, lh, rh])


# ============ STATE ============
_sequence = []
_stable_count = 0
_last_action = None
_detected_action = None
_confidence = 0.0
_hand_missing_count = 0
_action_locked = False

HAND_MISSING_RESET = 10


def reset_detection():
    global _sequence, _stable_count, _last_action, _detected_action
    global _confidence, _hand_missing_count, _action_locked
    _sequence = []; _stable_count = 0; _last_action = None
    _detected_action = None; _confidence = 0.0
    _hand_missing_count = 0; _action_locked = False


# ============ KONSTANTA WARNA (BGR) ============
C_BIRU = (122, 43, 0)
C_EMAS = (23, 160, 212)
C_HIJAU = (70, 190, 50)
C_MERAH = (0, 0, 180)
C_PUTIH = (240, 240, 240)
C_ABU = (150, 150, 150)
C_HITAM = (12, 12, 12)
F = cv2.FONT_HERSHEY_SIMPLEX  # satu font konsisten


def _blend(img, x1, y1, x2, y2, color, alpha=0.68):
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1: return
    roi = img[y1:y2, x1:x2]
    cv2.addWeighted(np.full(roi.shape, color, np.uint8),
                     alpha, roi, 1 - alpha, 0, roi)
    img[y1:y2, x1:x2] = roi


def _text_size(text, fs, th=1):
    return cv2.getTextSize(text, F, fs, th)[0]


# ============ PANEL KIRI ATAS ============
def draw_info_panel(img, fps, ada_tangan, action, conf, stable, total, locked):
    """
    Panel kecil di pojok kiri atas.
    Berisi: status tangan | isyarat | confidence | progress bar stabil.
    Hanya ditampilkan satu panel — tidak ada elemen lain.
    """
    h, w = img.shape[:2]
    k = w / 1280.0  # scale relatif 1280px base
    pad = int(10 * k)
    lh = int(20 * k)  # line height
    fs = max(0.38, 0.44 * k)  # font size — konsisten semua baris
    th = 1

    # Baris yang akan ditampilkan
    lines = []

    # Status tangan
    if ada_tangan:
        lines.append(("Tangan terdeteksi", C_PUTIH))
    else:
        lines.append(("Tangan tidak terdeteksi", C_ABU))

    # Isyarat + confidence (hanya kalau ada tangan)
    if ada_tangan and action and action != "-":
        conf_pct = f"{conf*100:.0f}%"
        if conf >= CONFIDENCE_THRESHOLD:
            lines.append((f"Isyarat: {action} {conf_pct}", C_PUTIH))
        else:
            lines.append((f"Isyarat tidak dikenal {conf_pct}", C_ABU))
    elif ada_tangan:
        lines.append(("Menganalisis gestur...", C_ABU))

    # Status stabil (hanya kalau confidence tinggi dan belum locked)
    if ada_tangan and conf >= CONFIDENCE_THRESHOLD and not locked:
        pct = int(stable / total * 100)
        lines.append((f"Stabil: {stable}/{total} ({pct}%)", C_PUTIH))

    # Locked
    if locked:
        lines.append((f"Terdeteksi: {_detected_action}", C_HIJAU))

    # FPS di baris terakhir
    lines.append((f"FPS: {fps}", C_ABU))

    if not lines:
        return

    # Hitung lebar panel berdasarkan teks terpanjang
    max_tw = max(_text_size(t, fs, th)[0] for t, _ in lines)
    pw = max_tw + pad * 2
    n_bar = 1 if (ada_tangan and conf >= CONFIDENCE_THRESHOLD and not locked) else 0
    bar_h = int(5 * k)
    ph = pad + len(lines) * lh + n_bar * (bar_h + int(4*k)) + pad

    x1, y1 = int(12*k), int(12*k)
    x2, y2 = x1 + pw, y1 + ph

    # Background semi-transparan
    _blend(img, x1, y1, x2, y2, C_HITAM, 0.65)

    # Border kiri — aksen biru
    cv2.rectangle(img, (x1, y1), (x1 + max(2, int(3*k)), y2), C_BIRU, -1)

    # Tulis baris
    bar_drawn = False
    cy = y1 + pad
    for i, (text, color) in enumerate(lines):
        tw, tv = _text_size(text, fs, th)
        cv2.putText(img, text, (x1 + pad + int(4*k), cy + tv),
                    F, fs, color, th, cv2.LINE_AA)
        cy += lh

        # Progress bar setelah baris "Stabil" — tipis
        if not bar_drawn and ada_tangan and conf >= CONFIDENCE_THRESHOLD and not locked:
            if "Stabil" in text:
                bx1 = x1 + pad + int(4*k)
                bx2 = x2 - pad
                by1 = cy
                by2 = by1 + bar_h
                _blend(img, bx1, by1, bx2, by2, (40, 40, 40), 1.0)
                fw = int((bx2 - bx1) * (stable / total))
                if fw > 0:
                    # Gradasi biru→emas
                    for j in range(fw):
                        t2 = j / max(fw, 1)
                        b2 = int(122*(1-t2)+23*t2)
                        g2 = int(43*(1-t2)+160*t2)
                        r2 = int(0*(1-t2)+212*t2)
                        cv2.line(img, (bx1+j, by1), (bx1+j, by2), (b2, g2, r2), 1)
                cy += bar_h + int(4*k)
                bar_drawn = True


# ============ FPS counter ============
_fps_t = time.time()
_fps_c = 0
_fps = 0


# Kelompok gesture per tahap — dipakai buat batasi prediksi model supaya
# gak "kebingungan" mikirin gesture yang gak relevan di tahap tsb.
GESTURE_LAYANAN = ['KTP', 'KK', 'AKTA']
GESTURE_KONFIRMASI = ['YA', 'TIDAK']


def _indeks_aktif(mode):
    """Return daftar indeks ACTIONS yang relevan untuk mode saat ini.
    Kalau mode gak dikenali / None, kembalikan semua indeks (tidak dibatasi)."""
    if mode == 'layanan':
        nama = GESTURE_LAYANAN
    elif mode == 'konfirmasi':
        nama = GESTURE_KONFIRMASI
    else:
        return list(range(len(ACTIONS)))

    idxs = [ACTIONS.index(n) for n in nama if n in ACTIONS]
    return idxs if idxs else list(range(len(ACTIONS)))  # fallback aman


# ============ PROSES 1 FRAME (pengganti generate_frames()) ============
def process_frame(frame_b64, mode=None):
    """
    Terima 1 frame base64 dari browser (pengganti cap.read() di versi asli),
    lalu jalankan PERSIS logic yang sama seperti generate_frames(): deteksi
    MediaPipe, ekstraksi keypoint, prediksi model, gambar landmark + panel
    info. Kembalikan frame hasil (base64 JPEG) + state deteksi.

    frame_b64: string base64 TANPA prefix 'data:image/jpeg;base64,'
    mode: 'layanan' (cuma pertimbangkan KTP/KK/AKTA) atau
          'konfirmasi' (cuma pertimbangkan YA/TIDAK), atau None (semua gesture)
    """
    global _sequence, _stable_count, _last_action, _detected_action
    global _confidence, _hand_missing_count, _action_locked
    global _fps_t, _fps_c, _fps

    try:
        img_bytes = base64.b64decode(frame_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return {'error': 'frame tidak valid'}
    except Exception as e:
        return {'error': str(e)}

    # FPS
    _fps_c += 1
    now = time.time()
    if now - _fps_t >= 1.0:
        _fps = _fps_c; _fps_c = 0; _fps_t = now

    image, results = mediapipe_detection(frame)
    draw_landmarks(image, results)

    ada_tangan = (results.left_hand_landmarks is not None or
                  results.right_hand_landmarks is not None)

    cur_action = _last_action or "-"
    cur_conf = _confidence

    if not ada_tangan:
        _hand_missing_count += 1
        _confidence = 0.0; _stable_count = 0; _last_action = None
        if _hand_missing_count >= HAND_MISSING_RESET:
            _sequence = []
        cur_action = "-"; cur_conf = 0.0
    else:
        _hand_missing_count = 0
        keypoints = extract_keypoints(results)
        _sequence.append(keypoints)
        _sequence = _sequence[-SEQUENCE_LENGTH:]

        if len(_sequence) == SEQUENCE_LENGTH and model is not None and not _action_locked:
            pred = model.predict(np.expand_dims(_sequence, 0), verbose=0)[0]
            idxs_aktif = _indeks_aktif(mode)
            local_idx = int(np.argmax(pred[idxs_aktif]))
            idx = idxs_aktif[local_idx]
            conf = float(pred[idx])
            action = ACTIONS[idx]
            _confidence = conf; cur_conf = conf; cur_action = action

            if conf >= CONFIDENCE_THRESHOLD:
                if action == _last_action: _stable_count += 1
                else: _stable_count = 1; _last_action = action

                if _stable_count >= STABLE_FRAMES:
                    _detected_action = action
                    _action_locked = True
                    _stable_count = 0
            else:
                _stable_count = 0; _last_action = None

    # Flip untuk tampilan (mirror) — tidak mempengaruhi hasil deteksi,
    # karena MediaPipe & ekstraksi keypoint sudah selesai di atas
    image = cv2.flip(image, 1)

    # ===== RENDER — hanya panel kiri atas =====
    try:
        draw_info_panel(image,
                         fps=_fps,
                         ada_tangan=ada_tangan,
                         action=cur_action,
                         conf=cur_conf,
                         stable=_stable_count,
                         total=STABLE_FRAMES,
                         locked=_action_locked)
    except Exception as e:
        import traceback
        print("[inference] GAGAL gambar panel:", e)
        traceback.print_exc()

    _, buf = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 88])
    frame_out_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')

    return {
        'frame': frame_out_b64,
        'ada_tangan': ada_tangan,
        'action': _last_action or '-',
        'confidence': round(_confidence * 100, 1),
        'stable': _stable_count,
        'total': STABLE_FRAMES,
        'locked': _action_locked,
        'detected_action': _detected_action,
    }


def get_detection_state():
    return {
        'action': _detected_action,
        'confidence': round(_confidence * 100, 1),
        'stable': _stable_count,
    }