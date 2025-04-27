import torch
import numpy as np

RANDOM_STATE = 42

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

TRAIN_END_DATE = '2022-03-30'
VALID_END_DATE = '2024-03-30'

NOISE_SCALE = 0.025
SMOTE_ALPHA_MIN = 0.5
SMOTE_ALPHA_MAX = 1.0

WINDOW_SIZE = 13
MIN_SAMPLES_PER_CLASS = 10

LSTM_EPOCHS_OPTIMIZED = 100
LSTM_EPOCHS_TRAINED = 100
TRANSFORMER_EPOCHS_OPTIMIZED = 100
TRANSFORMER_EPOCHS_TRAINED = 100

SVM_TRIALS = 180
LR_TRIALS = 180
LSTM_TRIALS = 40
TRANSFORMER_TRIALS = 40

SVM_PARAM_RANGES = {
    'C': np.logspace(-4, 2, 7),
    'kernel': ['linear', 'rbf', 'poly'],
    'gamma': np.logspace(-5, 0, 6),
    'class_weight': ['balanced'],
    'probability': [True],
    'tol': np.logspace(-2, 2, 5)
}

LR_PARAM_RANGES = {
    'C': np.logspace(-4, 2, 7),
    'solver': ['newton-cg', 'lbfgs', 'sag', 'saga'],
    'max_iter': [1000, 2000, 3000],
    'class_weight': ['balanced'],
    'tol': np.logspace(-2, 0, 3)
}

LSTM_PARAM_RANGES = {
    'hidden_size': (32, 96),
    'num_layers': (1, 2),
    'dropout': (0.2, 0.5),
    'learning_rate': (0.0005, 0.002),
    'batch_size': [16, 32, 64],
    'weight_decay': (1e-4, 1e-2)
}

TRANSFORMER_PARAM_RANGES = {
    'd_model': (32, 96),
    'num_layers': (1, 2),
    'dropout': (0.2, 0.5),
    'learning_rate': (0.0005, 0.002),
    'batch_size': [16, 32, 64],
    'nhead': [2, 4],
    'weight_decay': (1e-4, 1e-2)
}

FEATURE_COLUMNS = [
    'Date',
    "ret", "Volatility", "HL", "LO", "SR",
    "PM", "MDD","TVV","ATR", "SK", 
    "Median_HL", "variation_t", "ma7_t", "ma14_t", "ma21_t",
    "s_d7_t", "insec_t", "vnipc_t"
]
#label
#fore_di_rt
NUMBERS_FEATURES = 15

DATA_PATH = 'data/up_down.csv'
MODEL_PATH = 'models/model.joblib'
SCALER_PATH = 'models/scaler.joblib'
