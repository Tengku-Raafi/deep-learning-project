"""
config.py - Konfigurasi global project SIBI
"""
import numpy as np

# ============ DATA CONFIG ============
DATA_PATH        = 'MP_Data'
ACTIONS          = np.array(['KTP', 'KK', 'AKTA', 'YA', 'TIDAK'])
NO_SEQUENCES     = 75   # 3 orang x 25 sample per orang
SEQUENCE_LENGTH  = 30

# ============ MODEL CONFIG ============
N_FEATURES    = 258        # pose(132) + left_hand(63) + right_hand(63)
MODEL_PATH    = 'model_sibi.h5'
DATASET_PATH  = 'dataset.npz'

# ============ INFERENCE CONFIG ============
CONFIDENCE_THRESHOLD = 0.80  # sedikit diturunkan dari 0.80
STABLE_FRAMES        = 15