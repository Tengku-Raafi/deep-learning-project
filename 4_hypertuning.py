import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import itertools
import os
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.optimizers import Adam
from sklearn.metrics import accuracy_score
from config import ACTIONS, SEQUENCE_LENGTH, N_FEATURES, DATASET_PATH

print("=" * 60)
print("HYPERPARAMETER TUNING — LSTM SIBI")
print("=" * 60)

# ============ LOAD DATASET ============
data    = np.load(DATASET_PATH)
X_train = data['X_train']
X_test  = data['X_test']
y_train = data['y_train']
y_test  = data['y_test']
print(f"Train: {X_train.shape} | Test: {X_test.shape}\n")

# ============ GRID HYPERPARAMETER ============
# Setiap kombinasi akan dieksperimen
PARAM_GRID = {
    'lstm_units':    [64, 128],        # ukuran layer LSTM
    'dropout_rate':  [0.2, 0.4],       # dropout untuk regularisasi
    'learning_rate': [0.001, 0.0005],  # learning rate Adam
    'batch_size':    [16, 32],         # ukuran batch
}

# Buat semua kombinasi
keys   = list(PARAM_GRID.keys())
values = list(PARAM_GRID.values())
combinations = list(itertools.product(*values))
total = len(combinations)
print(f"Total kombinasi: {total}")
print(f"Estimasi waktu : ~{total * 2}-{total * 5} menit\n")

# ============ FUNGSI BUILD MODEL ============
def build_model(lstm_units, dropout_rate, learning_rate):
    model = Sequential([
        LSTM(lstm_units, return_sequences=True, activation='relu',
             input_shape=(SEQUENCE_LENGTH, N_FEATURES)),
        Dropout(dropout_rate),
        LSTM(lstm_units * 2, return_sequences=True, activation='relu'),
        Dropout(dropout_rate),
        LSTM(lstm_units, activation='relu'),
        Dropout(dropout_rate),
        Dense(64, activation='relu'),
        Dense(32, activation='relu'),
        Dense(len(ACTIONS), activation='softmax')
    ])
    model.compile(
        optimizer=Adam(learning_rate=learning_rate),
        loss='categorical_crossentropy',
        metrics=['categorical_accuracy']
    )
    return model

# ============ TUNING LOOP ============
results = []
best_acc    = 0
best_params = None
best_model  = None

for i, combo in enumerate(combinations):
    params = dict(zip(keys, combo))
    print(f"\n[{i+1}/{total}] Eksperimen: {params}")

    model = build_model(
        lstm_units    = params['lstm_units'],
        dropout_rate  = params['dropout_rate'],
        learning_rate = params['learning_rate']
    )

    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=15,
        restore_best_weights=True,
        verbose=0
    )

    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=100,
        batch_size=params['batch_size'],
        callbacks=[early_stop],
        verbose=0
    )

    # Evaluasi
    y_pred        = model.predict(X_test, verbose=0)
    y_pred_labels = np.argmax(y_pred, axis=1)
    y_test_labels = np.argmax(y_test, axis=1)
    acc           = accuracy_score(y_test_labels, y_pred_labels)

    epochs_done = len(history.history['loss'])
    val_loss    = min(history.history['val_loss'])

    print(f"  → Accuracy: {acc*100:.1f}% | Val Loss: {val_loss:.4f} | Epoch: {epochs_done}")

    results.append({
        'lstm_units':    params['lstm_units'],
        'dropout_rate':  params['dropout_rate'],
        'learning_rate': params['learning_rate'],
        'batch_size':    params['batch_size'],
        'accuracy':      round(acc, 4),
        'val_loss':      round(val_loss, 4),
        'epochs':        epochs_done
    })

    if acc > best_acc:
        best_acc    = acc
        best_params = params.copy()
        best_model  = model
        print(f"  ★ Model terbaik baru! Accuracy: {acc*100:.1f}%")

# ============ SIMPAN HASIL ============
df = pd.DataFrame(results)
df = df.sort_values('accuracy', ascending=False)
df.to_csv('hypertuning_results.csv', index=False)

print("\n" + "=" * 60)
print("HASIL HYPERPARAMETER TUNING")
print("=" * 60)
print(df.to_string(index=False))
print(f"\n★ Parameter terbaik: {best_params}")
print(f"★ Accuracy terbaik : {best_acc*100:.1f}%")

# Simpan model terbaik
if best_model:
    best_model.save('best_model.h5')
    print(f"Model terbaik disimpan: best_model.h5")

# ============ VISUALISASI ============
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('Hyperparameter Tuning Results', fontsize=14, fontweight='bold')

# Bar chart accuracy per kombinasi
labels_bar = [f"U{r['lstm_units']}\nD{r['dropout_rate']}\nLR{r['learning_rate']}\nB{r['batch_size']}"
              for _, r in df.iterrows()]
colors = ['#2563EB' if acc == df['accuracy'].max() else '#93C5FD'
          for acc in df['accuracy']]

axes[0].barh(range(len(df)), df['accuracy'] * 100, color=colors)
axes[0].set_yticks(range(len(df)))
axes[0].set_yticklabels(labels_bar, fontsize=8)
axes[0].set_xlabel('Accuracy (%)')
axes[0].set_title('Accuracy per Kombinasi')
axes[0].axvline(x=df['accuracy'].max() * 100, color='red', linestyle='--', alpha=0.5)
for idx, val in enumerate(df['accuracy']):
    axes[0].text(val * 100 + 0.3, idx, f'{val*100:.1f}%', va='center', fontsize=8)

# Scatter accuracy vs val_loss
scatter = axes[1].scatter(df['val_loss'], df['accuracy'] * 100,
                          c=df['lstm_units'], cmap='Blues', s=100, alpha=0.8)
plt.colorbar(scatter, ax=axes[1], label='LSTM Units')
axes[1].set_xlabel('Validation Loss')
axes[1].set_ylabel('Accuracy (%)')
axes[1].set_title('Accuracy vs Val Loss')
# Tandai yang terbaik
best_row = df.iloc[0]
axes[1].scatter(best_row['val_loss'], best_row['accuracy'] * 100,
                color='red', s=200, zorder=5, marker='*', label='Terbaik')
axes[1].legend()

plt.tight_layout()
plt.savefig('hypertuning_results.png', dpi=120, bbox_inches='tight')
print(f"\nVisualisasi disimpan: hypertuning_results.png")
print(f"Hasil CSV disimpan : hypertuning_results.csv")
print("\nLanjut: python 5_testing.py")