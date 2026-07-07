import cv2
import numpy as np
import os
import time
import mediapipe as mp
from config import DATA_PATH, ACTIONS, SEQUENCE_LENGTH

mp_holistic = mp.solutions.holistic
mp_drawing  = mp.solutions.drawing_utils

# ============ CONFIG ORANG ============
ORANG           = ['Orang 1', 'Orang 2', 'Orang 3']
SAMPLE_PERORANG = 25
TOTAL_SAMPLES   = len(ORANG) * SAMPLE_PERORANG  # 75

# ============ FUNGSI ============
def mediapipe_detection(image, model):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False
    results = model.process(image)
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    return image, results

def draw_landmarks(image, results):
    mp_drawing.draw_landmarks(
        image, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS,
        mp_drawing.DrawingSpec(color=(121, 22, 76),  thickness=2, circle_radius=4),
        mp_drawing.DrawingSpec(color=(121, 44, 250), thickness=2, circle_radius=2)
    )
    mp_drawing.draw_landmarks(
        image, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS,
        mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=4),
        mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
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

def layar_jeda(cap, holistic, judul, subjudul):
    print(f"\n  {judul}")
    print(f"  {subjudul}")
    print("  Tekan SPASI di jendela kamera untuk lanjutkan...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        _, results = mediapipe_detection(frame, holistic)
        draw_landmarks(frame, results)
        cv2.putText(frame, judul, (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, subjudul, (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2, cv2.LINE_AA)
        cv2.putText(frame, 'Tekan SPASI untuk lanjut', (20, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.imshow('Rekam Isyarat SIBI', frame)
        key = cv2.waitKey(10) & 0xFF
        if key == ord(' '):
            break
        if key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            exit()

    for hitung in range(3, 0, -1):
        deadline = time.time() + 1.0
        while time.time() < deadline:
            ret, frame = cap.read()
            if not ret:
                break
            _, results = mediapipe_detection(frame, holistic)
            draw_landmarks(frame, results)
            h, w = frame.shape[:2]
            cv2.putText(frame, str(hitung), (w//2 - 40, h//2 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 255, 0), 8, cv2.LINE_AA)
            cv2.putText(frame, judul, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)
            cv2.imshow('Rekam Isyarat SIBI', frame)
            cv2.waitKey(1)

# ============ BUAT FOLDER ============
for action in ACTIONS:
    for seq in range(TOTAL_SAMPLES):
        os.makedirs(os.path.join(DATA_PATH, action, str(seq)), exist_ok=True)

# ============ INFO AWAL ============
print("=" * 60)
print("  REKAM DATA ISYARAT — 3 ORANG")
print(f"  Kelas      : {list(ACTIONS)}")
print(f"  Per orang  : {SAMPLE_PERORANG} sample")
print(f"  Total/kelas: {TOTAL_SAMPLES} sample ({len(ORANG)} orang x {SAMPLE_PERORANG})")
print(f"  Per sample : {SEQUENCE_LENGTH} frame (hanya frame valid)")
print(f"  Grand total: {len(ACTIONS) * TOTAL_SAMPLES} rekaman")
print("=" * 60)
input("  Tekan ENTER untuk mulai...")

# ============ BUKA KAMERA ============
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("ERROR: Webcam tidak terdeteksi!")
    exit()

# ============ REKAM ============
with mp_holistic.Holistic(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as holistic:

    for action_idx, action in enumerate(ACTIONS):

        layar_jeda(
            cap, holistic,
            f"KELAS: {action}  ({action_idx + 1}/{len(ACTIONS)})",
            f"Siapkan diri — rekam {TOTAL_SAMPLES} sample ({len(ORANG)} orang x {SAMPLE_PERORANG})"
        )

        for orang_idx, nama_orang in enumerate(ORANG):

            layar_jeda(
                cap, holistic,
                f"{action}  —  {nama_orang}  ({orang_idx + 1}/{len(ORANG)})",
                f"Rekam {SAMPLE_PERORANG} sample  |  Isyarat: {action}"
            )

            sample_offset = orang_idx * SAMPLE_PERORANG

            for sequence in range(SAMPLE_PERORANG):
                global_seq = sample_offset + sequence

                # Tampilkan "SIAP-SIAP" dulu sebelum mulai rekam
                for _ in range(30):  # ~0.5 detik preview
                    ret, frame = cap.read()
                    if not ret: break
                    image, results = mediapipe_detection(frame, holistic)
                    draw_landmarks(image, results)
                    cv2.putText(image, 'SIAP-SIAP...', (100, 220),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 255, 0), 4, cv2.LINE_AA)
                    cv2.putText(image,
                                f'{action}  |  {nama_orang}  |  Sample {sequence + 1}/{SAMPLE_PERORANG}',
                                (15, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)
                    cv2.imshow('Rekam Isyarat SIBI', image)
                    cv2.waitKey(10)

                # ===== REKAM FRAME — hanya simpan kalau tangan kedeteksi =====
                frame_num = 0
                while frame_num < SEQUENCE_LENGTH:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    image, results = mediapipe_detection(frame, holistic)
                    draw_landmarks(image, results)

                    tangan_ok = (results.left_hand_landmarks is not None or
                                 results.right_hand_landmarks is not None)

                    if not tangan_ok:
                        # Tangan tidak kedeteksi — tampilkan warning, JANGAN simpan
                        cv2.putText(image, '!! TANGAN TIDAK TERDETEKSI !!', (60, 200),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3, cv2.LINE_AA)
                        cv2.putText(image, 'Masukkan tangan ke frame kamera',
                                    (80, 245), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                                    (0, 165, 255), 2, cv2.LINE_AA)
                        cv2.putText(image,
                                    f'{action}  |  {nama_orang}  |  '
                                    f'Sample {sequence + 1}/{SAMPLE_PERORANG}  |  '
                                    f'Frame {frame_num}/{SEQUENCE_LENGTH - 1}',
                                    (15, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                                    (0, 255, 255), 2, cv2.LINE_AA)
                        cv2.imshow('Rekam Isyarat SIBI', image)
                        cv2.waitKey(10)
                        continue  # ulang frame ini, tidak increment frame_num

                    # Tangan kedeteksi — simpan dan lanjut ke frame berikutnya
                    keypoints = extract_keypoints(results)
                    np.save(
                        os.path.join(DATA_PATH, action, str(global_seq), str(frame_num)),
                        keypoints
                    )

                    cv2.putText(image,
                                f'{action}  |  {nama_orang}  |  '
                                f'Sample {sequence + 1}/{SAMPLE_PERORANG}  |  '
                                f'Frame {frame_num}/{SEQUENCE_LENGTH - 1}',
                                (15, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                                (0, 255, 255), 2, cv2.LINE_AA)
                    cv2.imshow('Rekam Isyarat SIBI', image)

                    frame_num += 1  # hanya naik kalau tangan kedeteksi

                    if cv2.waitKey(10) & 0xFF == ord('q'):
                        print("\nDibatalkan oleh user.")
                        cap.release()
                        cv2.destroyAllWindows()
                        exit()

                print(f"    ✓ {nama_orang} Sample {sequence + 1}/{SAMPLE_PERORANG} selesai")

        print(f"  ✓ {action} — semua orang selesai ({TOTAL_SAMPLES} sample)\n")

# ============ SELESAI ============
cap.release()
cv2.destroyAllWindows()
print("\n" + "=" * 60)
print("  REKAMAN SELESAI!")
print(f"  Data tersimpan di: {DATA_PATH}/")
print(f"  Total sample/kelas: {TOTAL_SAMPLES}")
print("  Lanjut: python 2_preprocess.py")
print("=" * 60)