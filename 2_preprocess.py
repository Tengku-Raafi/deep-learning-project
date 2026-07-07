import numpy as np
import os
from sklearn.model_selection import train_test_split
from tensorflow.keras.utils import to_categorical
from config import DATA_PATH, ACTIONS, NO_SEQUENCES, SEQUENCE_LENGTH, DATASET_PATH

print("=" * 60)
print("PREPROCESSING DATA")
print("=" * 60)

label_map = {label: num for num, label in enumerate(ACTIONS)}
print(f"Label map: {label_map}")

sequences, labels = [], []
for action in ACTIONS:
    for sequence in range(NO_SEQUENCES):
        window = []
        for frame_num in range(SEQUENCE_LENGTH):
            path = os.path.join(DATA_PATH, action, str(sequence), f'{frame_num}.npy')
            if not os.path.exists(path):
                print(f"WARNING: File hilang: {path}")
                continue
            res = np.load(path)
            window.append(res)
        if len(window) == SEQUENCE_LENGTH:
            sequences.append(window)
            labels.append(label_map[action])

X = np.array(sequences)
y = to_categorical(labels).astype(int)

print(f"\nShape X: {X.shape}  (sample, frame, features)")
print(f"Shape y: {y.shape}  (sample, kelas)")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, stratify=labels, random_state=42
)

print(f"\nTrain: {X_train.shape}")
print(f"Test : {X_test.shape}")

np.savez(DATASET_PATH, X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test)
print(f"\nDataset disimpan ke: {DATASET_PATH}")
print("Lanjut: python 3_train_model.py")