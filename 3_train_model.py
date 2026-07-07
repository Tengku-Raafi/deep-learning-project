import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.metrics import classification_report, confusion_matrix
from config import ACTIONS, SEQUENCE_LENGTH, N_FEATURES, MODEL_PATH, DATASET_PATH

print("=" * 60)
print("TRAINING MODEL LSTM")
print("=" * 60)

# Load dataset
data = np.load(DATASET_PATH)
X_train, X_test = data['X_train'], data['X_test']
y_train, y_test = data['y_train'], data['y_test']
print(f"Train: {X_train.shape}, Test: {X_test.shape}")

# Build model
model = Sequential([
    LSTM(64, return_sequences=True, activation='relu', input_shape=(SEQUENCE_LENGTH, N_FEATURES)),
    LSTM(128, return_sequences=True, activation='relu'),
    LSTM(64, activation='relu'),
    Dense(64, activation='relu'),
    Dense(32, activation='relu'),
    Dense(len(ACTIONS), activation='softmax')
])

model.compile(
    optimizer='adam', 
    loss='categorical_crossentropy', 
    metrics=['categorical_accuracy'])
model.summary()

callbacks = [
    EarlyStopping(
        monitor='val_loss', 
        patience=20, restore_best_weights=True),
    ModelCheckpoint(
        MODEL_PATH, 
        monitor='val_categorical_accuracy', 
        save_best_only=True, verbose=1)
]

history = model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=200,
    batch_size=16,
    callbacks=callbacks,
    verbose=1
)

# Evaluasi final
print("\n" + "=" * 60)
print("EVALUASI FINAL")
print("=" * 60)

y_pred = model.predict(X_test)
y_pred_classes = np.argmax(y_pred, axis=1)
y_test_classes = np.argmax(y_test, axis=1)

print("\nClassification Report:")
print(classification_report(y_test_classes, y_pred_classes, target_names=ACTIONS))

print("\nConfusion Matrix:")
cm = confusion_matrix(y_test_classes, y_pred_classes)
print(cm)

# Plot
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].plot(history.history['loss'], label='Train')
axes[0].plot(history.history['val_loss'], label='Val')
axes[0].set_title('Loss'); axes[0].legend()
axes[1].plot(history.history['categorical_accuracy'], label='Train')
axes[1].plot(history.history['val_categorical_accuracy'], label='Val')
axes[1].set_title('Accuracy'); axes[1].legend()
plt.tight_layout()
plt.savefig('training_history.png')
print(f"\nPlot disimpan: training_history.png")
print(f"Model disimpan: {MODEL_PATH}")