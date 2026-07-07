import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import os
from tensorflow.keras.models import load_model
from sklearn.metrics import (classification_report, confusion_matrix,
                              accuracy_score, precision_score,
                              recall_score, f1_score)
from config import ACTIONS, DATASET_PATH, MODEL_PATH

print("=" * 60)
print("TESTING & EVALUASI MODEL LSTM SIBI")
print("=" * 60)

# ============ LOAD MODEL ============
# Prioritas: best_model.h5 dari hypertuning, fallback ke model_sibi.h5
MODEL_TEST = 'best_model.h5' if os.path.exists('best_model.h5') else MODEL_PATH
print(f"Model yang diuji: {MODEL_TEST}")

model = load_model(MODEL_TEST)
model.summary()

# ============ LOAD DATASET ============
data    = np.load(DATASET_PATH)
X_train = data['X_train']
X_test  = data['X_test']
y_train = data['y_train']
y_test  = data['y_test']

print(f"\nTrain set: {X_train.shape}")
print(f"Test set : {X_test.shape}")

# ============ PREDIKSI ============
y_pred_prob   = model.predict(X_test, verbose=1)
y_pred_labels = np.argmax(y_pred_prob, axis=1)
y_test_labels = np.argmax(y_test, axis=1)

# Evaluasi training set juga (untuk cek overfitting)
y_train_pred  = model.predict(X_train, verbose=0)
y_train_pred_labels = np.argmax(y_train_pred, axis=1)
y_train_labels      = np.argmax(y_train, axis=1)

# ============ METRIK UTAMA ============
acc_test  = accuracy_score(y_test_labels, y_pred_labels)
acc_train = accuracy_score(y_train_labels, y_train_pred_labels)
prec      = precision_score(y_test_labels, y_pred_labels, average='weighted', zero_division=0)
rec       = recall_score(y_test_labels, y_pred_labels, average='weighted', zero_division=0)
f1        = f1_score(y_test_labels, y_pred_labels, average='weighted', zero_division=0)

print("\n" + "=" * 60)
print("METRIK EVALUASI")
print("=" * 60)
print(f"  Accuracy Train : {acc_train*100:.2f}%")
print(f"  Accuracy Test  : {acc_test*100:.2f}%")
print(f"  Selisih        : {(acc_train - acc_test)*100:.2f}% ", end="")
if (acc_train - acc_test) > 0.15:
    print("⚠ Kemungkinan overfitting")
else:
    print("✓ Tidak overfitting")
print(f"  Precision      : {prec*100:.2f}%")
print(f"  Recall         : {rec*100:.2f}%")
print(f"  F1-Score       : {f1*100:.2f}%")

# ============ CLASSIFICATION REPORT ============
print("\n" + "=" * 60)
print("CLASSIFICATION REPORT PER KELAS")
print("=" * 60)
report = classification_report(
    y_test_labels, y_pred_labels,
    target_names=ACTIONS,
    zero_division=0
)
print(report)

# ============ AKURASI PER KELAS ============
print("AKURASI PER KELAS")
print("=" * 60)
cm = confusion_matrix(y_test_labels, y_pred_labels)
acc_per_kelas = cm.diagonal() / cm.sum(axis=1)
for i, (action, acc) in enumerate(zip(ACTIONS, acc_per_kelas)):
    bar  = '█' * int(acc * 20)
    sisa = '░' * (20 - int(acc * 20))
    status = '✓' if acc >= 0.75 else '⚠'
    print(f"  {status} {action:6s} : {bar}{sisa} {acc*100:.1f}%")

# ============ SIMPAN REPORT KE TXT ============
with open('testing_report.txt', 'w') as f:
    f.write("=" * 60 + "\n")
    f.write("TESTING REPORT — LSTM SIBI\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"Model       : {MODEL_TEST}\n")
    f.write(f"Test samples: {len(y_test_labels)}\n\n")
    f.write(f"Accuracy Train : {acc_train*100:.2f}%\n")
    f.write(f"Accuracy Test  : {acc_test*100:.2f}%\n")
    f.write(f"Precision      : {prec*100:.2f}%\n")
    f.write(f"Recall         : {rec*100:.2f}%\n")
    f.write(f"F1-Score       : {f1*100:.2f}%\n\n")
    f.write("Classification Report:\n")
    f.write(report + "\n")
    f.write("Confusion Matrix:\n")
    f.write(str(cm) + "\n")

print(f"\nReport disimpan: testing_report.txt")

# ============ VISUALISASI ============
fig = plt.figure(figsize=(16, 12))
fig.suptitle('Testing & Evaluasi Model LSTM SIBI', fontsize=16, fontweight='bold', y=0.98)

# --- 1. Confusion Matrix ---
ax1 = fig.add_subplot(2, 2, 1)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=ACTIONS, yticklabels=ACTIONS, ax=ax1,
            linewidths=0.5, linecolor='white')
ax1.set_title('Confusion Matrix', fontweight='bold', pad=10)
ax1.set_ylabel('Label Sebenarnya')
ax1.set_xlabel('Label Prediksi')

# --- 2. Confusion Matrix Normalisasi (%) ---
ax2 = fig.add_subplot(2, 2, 2)
cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
cm_norm = np.nan_to_num(cm_norm)
sns.heatmap(cm_norm, annot=True, fmt='.1%', cmap='Greens',
            xticklabels=ACTIONS, yticklabels=ACTIONS, ax=ax2,
            linewidths=0.5, linecolor='white', vmin=0, vmax=1)
ax2.set_title('Confusion Matrix (Normalisasi)', fontweight='bold', pad=10)
ax2.set_ylabel('Label Sebenarnya')
ax2.set_xlabel('Label Prediksi')

# --- 3. Akurasi per kelas ---
ax3 = fig.add_subplot(2, 2, 3)
colors = ['#16A34A' if a >= 0.75 else '#D97706' if a >= 0.5 else '#CC0000'
          for a in acc_per_kelas]
bars = ax3.bar(ACTIONS, acc_per_kelas * 100, color=colors, edgecolor='white', linewidth=1.5)
ax3.set_title('Akurasi per Kelas', fontweight='bold', pad=10)
ax3.set_ylabel('Accuracy (%)')
ax3.set_ylim(0, 110)
ax3.axhline(y=75, color='orange', linestyle='--', alpha=0.7, label='Target 75%')
ax3.axhline(y=acc_test * 100, color='blue', linestyle='--', alpha=0.7,
            label=f'Rata-rata {acc_test*100:.1f}%')
for bar, acc in zip(bars, acc_per_kelas):
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
             f'{acc*100:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=10)
legend_patches = [
    mpatches.Patch(color='#16A34A', label='≥ 75% (Baik)'),
    mpatches.Patch(color='#D97706', label='50–75% (Cukup)'),
    mpatches.Patch(color='#CC0000', label='< 50% (Perlu improve)'),
]
ax3.legend(handles=legend_patches, loc='upper right', fontsize=8)

# --- 4. Metrik ringkasan ---
ax4 = fig.add_subplot(2, 2, 4)
metrik_nama = ['Accuracy\n(Train)', 'Accuracy\n(Test)', 'Precision', 'Recall', 'F1-Score']
metrik_val  = [acc_train*100, acc_test*100, prec*100, rec*100, f1*100]
bar_colors  = ['#93C5FD', '#2563EB', '#6EE7B7', '#34D399', '#059669']
bars2 = ax4.bar(metrik_nama, metrik_val, color=bar_colors, edgecolor='white', linewidth=1.5)
ax4.set_title('Ringkasan Metrik', fontweight='bold', pad=10)
ax4.set_ylabel('Score (%)')
ax4.set_ylim(0, 115)
ax4.axhline(y=80, color='red', linestyle='--', alpha=0.5, label='Target 80%')
for bar, val in zip(bars2, metrik_val):
    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
             f'{val:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=10)
ax4.legend(fontsize=8)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('testing_report.png', dpi=120, bbox_inches='tight')
plt.show()

print(f"Visualisasi disimpan: testing_report.png")
print("\n" + "=" * 60)

# ============ KESIMPULAN OTOMATIS ============
print("KESIMPULAN")
print("=" * 60)
if acc_test >= 0.90:
    print("  ✓ Model SANGAT BAIK — siap diimplementasi ke web")
elif acc_test >= 0.75:
    print("  ✓ Model CUKUP BAIK — bisa diimplementasi, monitor performanya")
elif acc_test >= 0.60:
    print("  ⚠ Model PERLU DITINGKATKAN")
    print("    Saran: tambah data training atau coba arsitektur berbeda")
else:
    print("  ✗ Model BELUM SIAP — accuracy terlalu rendah")
    print("    Saran: rekam ulang data dengan kualitas lebih baik")

kelas_buruk = [ACTIONS[i] for i, a in enumerate(acc_per_kelas) if a < 0.5]
if kelas_buruk:
    print(f"\n  ⚠ Kelas yang perlu perhatian: {kelas_buruk}")
    print("    Saran: tambah sample untuk kelas tersebut atau perjelas gerakan isyaratnya")
else:
    print("\n  ✓ Semua kelas terdeteksi dengan baik")

print(f"\n  Model siap: {MODEL_TEST}")
print("  Salin ke model_sibi.h5 jika belum, lalu restart server Flask")
print("=" * 60)