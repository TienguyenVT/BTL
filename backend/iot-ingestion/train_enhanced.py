# -*- coding: utf-8 -*-
"""
Script Huan Luyen Mo Hinh Machine Learning - Phien ban Rut gon.
Chi su dung 2 mo hinh: Random Forest va XGBoost.

Quy trinh:
  1. Doc du lieu tu MongoDB (collection: training_health_data)
  2. Feature Engineering (12 features)
  3. Baseline: GridSearchCV (RF + XGBoost)
  4. Optuna: RF + XGBoost Bayesian Optimization
  5. So sanh va chon mo hinh tot nhat
  6. Retrain tren 100% data + luu ket qua
"""

import os
import sys
import warnings
import time as time_module
import pandas as pd
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime

from sklearn.model_selection import (
    train_test_split, cross_val_score, StratifiedKFold,
    GridSearchCV
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score,
    f1_score, precision_score, recall_score
)

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("[TRAIN] W XGBoost khong duoc cai dat. Bo qua XGBoost.")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    print("[TRAIN] W Optuna khong duoc cai dat. Bo qua Bayesian Optimization.")

from config import settings
from database import db_connection

warnings.filterwarnings('ignore')


# ══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def ensure_results_dir():
    results_dir = os.path.join(os.path.dirname(__file__), 'result')
    os.makedirs(results_dir, exist_ok=True)
    return results_dir


def save_figure(fig, name, results_dir):
    path = os.path.join(results_dir, name)
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"[TRAIN] [OK] Da luu: {path}")


def plot_physiological_distributions(df, results_dir):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Phan bo chi so sinh ly theo nhan (Training Data)', fontsize=16, fontweight='bold')
    for ax, col, title in zip(axes.flat,
                               ['bpm', 'gsr_adc', 'body_temp', 'spo2'],
                               ['Nhip tim (BPM)', 'Dien tro da (GSR)', 'Nhiet do (Body_Temp)', 'SpO2']):
        sns.boxplot(ax=ax, x='intended_label', y=col, data=df, palette='Set2')
        ax.set_title(title)
    save_figure(fig, '01_physiological_distributions.png', results_dir)


def plot_correlation_matrix(df, features, results_dir):
    corr_cols = [c for c in features if c in df.columns]
    available = [c for c in corr_cols if c in df.columns]
    if len(available) < 2:
        return
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(df[available].corr(), annot=True, cmap='coolwarm',
                fmt='.2f', linewidths=0.5, square=True, vmin=-1, vmax=1, ax=ax)
    ax.set_title('Ma tran tuong quan', fontsize=14, fontweight='bold')
    save_figure(fig, '02_correlation_matrix.png', results_dir)


def plot_confusion_matrix(y_true, y_pred, classes, results_dir, name='03_confusion_matrix.png'):
    fig, ax = plt.subplots(figsize=(8, 6))
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=classes, yticklabels=classes, ax=ax)
    ax.set_title('Ma tran nham lan (Confusion Matrix)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Nhan du doan')
    ax.set_ylabel('Nhan thuc te')
    save_figure(fig, name, results_dir)


def plot_feature_importance(model, feature_names, results_dir, title='Do quan trong dac trung'):
    fig, ax = plt.subplots(figsize=(10, 6))
    imp = pd.Series(model.feature_importances_, index=feature_names).sort_values(ascending=True)
    imp.plot(kind='barh', ax=ax, color='steelblue')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Diem quan trong')
    save_figure(fig, '04_feature_importance.png', results_dir)


def plot_cv_comparison(cv_results_dict, results_dir):
    names = list(cv_results_dict.keys())
    means = [cv_results_dict[n]['f1_mean'] * 100 for n in names]
    stds = [cv_results_dict[n]['f1_std'] * 100 for n in names]
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(names, means, yerr=stds, capsize=5, color='steelblue', alpha=0.8)
    ax.set_ylim(0, 105)
    ax.set_title('So sanh F1-Score (weighted) - Cross-Validation', fontsize=14, fontweight='bold')
    ax.set_ylabel('F1-Score (%)')
    for bar, m in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{m:.2f}%', ha='center', va='bottom', fontsize=10)
    save_figure(fig, '05_cv_comparison.png', results_dir)


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════

def create_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    df_e = df.copy()
    eps = 1e-6
    df_e['bpm_spo2_ratio'] = df_e['bpm'] / (df_e['spo2'] + eps)
    df_e['temp_gsr_interaction'] = df_e['body_temp'] * df_e['gsr_adc'] / 1000
    df_e['bpm_temp_product'] = df_e['bpm'] * df_e['body_temp']
    df_e['spo2_gsr_ratio'] = df_e['spo2'] / (df_e['gsr_adc'] + eps)
    df_e['bpm_deviation'] = np.abs(df_e['bpm'] - 75)
    df_e['temp_deviation'] = np.abs(df_e['body_temp'] - 36.8)
    df_e['gsr_deviation'] = np.abs(df_e['gsr_adc'] - 2200)
    df_e['physiological_stress_index'] = (
        (df_e['bpm'] - 75) / 75 + (df_e['gsr_adc'] - 2200) / 2200
    )
    return df_e


# ══════════════════════════════════════════════════════════════════════════════
# BASELINE: GRIDSEARCHCV (Original approach)
# ══════════════════════════════════════════════════════════════════════════════

def baseline_gridsearch_rf(X_train, y_train, cv_folds=3):
    print("\n" + "=" * 60)
    print("  BASELINE: GridSearchCV - RandomForest")
    print("=" * 60)
    # Grid nho (54 combos) - co max_features, bootstrap nhung khong qua lon
    param_grid = {
        'n_estimators': [100, 300],
        'max_depth': [10, 20, None],
        'min_samples_split': [2, 10],
        'min_samples_leaf': [1, 4],
        'class_weight': [None, 'balanced'],
        'max_features': ['sqrt', 'log2'],
        'bootstrap': [True],
    }
    print(f"  Grid: {len(param_grid['n_estimators'])}x{len(param_grid['max_depth'])}x{len(param_grid['min_samples_split'])}x{len(param_grid['min_samples_leaf'])}x{len(param_grid['class_weight'])}x{len(param_grid['max_features'])}x{len(param_grid['bootstrap'])} = {len(param_grid['n_estimators'])*len(param_grid['max_depth'])*len(param_grid['min_samples_split'])*len(param_grid['min_samples_leaf'])*len(param_grid['class_weight'])*len(param_grid['max_features'])*len(param_grid['bootstrap'])} combos")
    base = RandomForestClassifier(random_state=42, n_jobs=-1)
    grid = GridSearchCV(base, param_grid, cv=cv_folds, scoring='f1_weighted',
                        n_jobs=-1, verbose=1, refit=True)
    t0 = time_module.time()
    grid.fit(X_train, y_train)
    elapsed = time_module.time() - t0
    print(f"\n  Best params: {grid.best_params_}")
    print(f"  Best CV F1: {grid.best_score_*100:.2f}%")
    print(f"  Thoi gian: {elapsed:.1f}s")
    return grid.best_estimator_, grid.best_params_, grid.best_score_, elapsed


def baseline_gridsearch_xgb(X_train, y_train_enc, cv_folds=3):
    if not XGBOOST_AVAILABLE:
        return None, None, None, 0
    print("\n" + "=" * 60)
    print("  BASELINE: GridSearchCV - XGBoost (expanded grid)")
    print("=" * 60)
    # Grid nho (96 combos) - chi giu regularization params moi
    param_grid = {
        'n_estimators': [100, 200],
        'max_depth': [5, 10],
        'learning_rate': [0.05, 0.1],
        'subsample': [0.8, 1.0],
        'colsample_bytree': [0.8, 1.0],
        'gamma': [0, 0.5],
        'reg_alpha': [0, 1.0],
        'reg_lambda': [1, 5],
    }
    print(f"  Grid: {len(param_grid['n_estimators'])}x{len(param_grid['max_depth'])}x{len(param_grid['learning_rate'])}x{len(param_grid['subsample'])}x{len(param_grid['colsample_bytree'])}x{len(param_grid['gamma'])}x{len(param_grid['reg_alpha'])}x{len(param_grid['reg_lambda'])} = {len(param_grid['n_estimators'])*len(param_grid['max_depth'])*len(param_grid['learning_rate'])*len(param_grid['subsample'])*len(param_grid['colsample_bytree'])*len(param_grid['gamma'])*len(param_grid['reg_alpha'])*len(param_grid['reg_lambda'])} combos")
    base = XGBClassifier(random_state=42, n_jobs=-1, eval_metric='mlogloss',
                         verbosity=0, use_label_encoder=False)
    grid = GridSearchCV(base, param_grid, cv=cv_folds, scoring='f1_weighted',
                        n_jobs=-1, verbose=1, refit=True)
    t0 = time_module.time()
    print(f"  Bat dau GridSearch XGBoost luc {datetime.now().strftime('%H:%M:%S')}...")
    grid.fit(X_train, y_train_enc)
    elapsed = time_module.time() - t0
    print(f"\n  Best params: {grid.best_params_}")
    print(f"  Best CV F1: {grid.best_score_*100:.2f}%")
    print(f"  Thoi gian: {elapsed:.1f}s")
    return grid.best_estimator_, grid.best_params_, grid.best_score_, elapsed


# ══════════════════════════════════════════════════════════════════════════════
# OPTUNA: BAYESIAN OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════════

def optuna_rf_objective(X_train, y_train, trial):
    n_estimators = trial.suggest_int('n_estimators', 100, 500, step=50)
    max_depth = trial.suggest_int('max_depth', 5, 30)
    min_samples_split = trial.suggest_int('min_samples_split', 2, 20)
    min_samples_leaf = trial.suggest_int('min_samples_leaf', 1, 10)
    max_features = trial.suggest_categorical('max_features', ['sqrt', 'log2', None])
    class_weight = trial.suggest_categorical('class_weight', [None, 'balanced'])
    model = RandomForestClassifier(
        n_estimators=n_estimators, max_depth=max_depth,
        min_samples_split=min_samples_split, min_samples_leaf=min_samples_leaf,
        max_features=max_features, class_weight=class_weight,
        random_state=42, n_jobs=-1
    )
    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    score = cross_val_score(model, X_train, y_train, cv=skf,
                           scoring='f1_weighted', n_jobs=-1).mean()
    trial.set_user_attr('f1', score)
    print(f"    [RF Trial {trial.number}] F1={score*100:.2f}% | n={n_estimators}, d={max_depth}", flush=True)
    return score


def optuna_xgb_objective(X_train, y_train_enc, trial):
    n_estimators = trial.suggest_int('n_estimators', 100, 500, step=50)
    max_depth = trial.suggest_int('max_depth', 3, 15)
    learning_rate = trial.suggest_float('learning_rate', 0.01, 0.3, log=True)
    subsample = trial.suggest_float('subsample', 0.6, 1.0)
    colsample_bytree = trial.suggest_float('colsample_bytree', 0.6, 1.0)
    gamma = trial.suggest_float('gamma', 0, 2.0)
    reg_alpha = trial.suggest_float('reg_alpha', 1e-4, 10.0, log=True)
    reg_lambda = trial.suggest_float('reg_lambda', 1e-4, 10.0, log=True)
    min_child_weight = trial.suggest_int('min_child_weight', 1, 10)
    model = XGBClassifier(
        n_estimators=n_estimators, max_depth=max_depth,
        learning_rate=learning_rate, subsample=subsample,
        colsample_bytree=colsample_bytree, gamma=gamma,
        reg_alpha=reg_alpha, reg_lambda=reg_lambda,
        min_child_weight=min_child_weight,
        random_state=42, n_jobs=-1, eval_metric='mlogloss', verbosity=0,
        use_label_encoder=False
    )
    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    score = cross_val_score(model, X_train, y_train_enc, cv=skf,
                           scoring='f1_weighted', n_jobs=-1).mean()
    trial.set_user_attr('f1', score)
    print(f"    [XGB Trial {trial.number}] F1={score*100:.2f}% | n={n_estimators}, d={max_depth}, lr={learning_rate:.3f}", flush=True)
    return score


def run_optuna_rf(X_train, y_train, n_trials=50):
    if not OPTUNA_AVAILABLE:
        return None, None, 0
    print("\n" + "=" * 60)
    print("  OPTUNA: Bayesian Optimization - RandomForest")
    print("=" * 60)
    t0 = time_module.time()
    print(f"  Bat dau luc {datetime.now().strftime('%H:%M:%S')} | {n_trials} trials...")
    study = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(lambda trial: optuna_rf_objective(X_train, y_train, trial),
                    n_trials=n_trials, show_progress_bar=False)
    elapsed = time_module.time() - t0
    best_params = study.best_params
    best_score = study.best_value
    print(f"  Best params: {best_params}")
    print(f"  Best CV F1: {best_score*100:.2f}%")
    print(f"  Thoi gian: {elapsed:.1f}s ({n_trials} trials)")
    model = RandomForestClassifier(**best_params, random_state=42, n_jobs=-1)
    return model, best_params, best_score, elapsed


def run_optuna_xgb(X_train, y_train_enc, n_trials=50):
    if not OPTUNA_AVAILABLE or not XGBOOST_AVAILABLE:
        return None, None, 0
    print("\n" + "=" * 60)
    print("  OPTUNA: Bayesian Optimization - XGBoost")
    print("=" * 60)
    t0 = time_module.time()
    print(f"  Bat dau luc {datetime.now().strftime('%H:%M:%S')} | {n_trials} trials...")
    study = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(lambda trial: optuna_xgb_objective(X_train, y_train_enc, trial),
                    n_trials=n_trials, show_progress_bar=False)
    elapsed = time_module.time() - t0
    best_params = study.best_params
    best_score = study.best_value
    print(f"  Best params: {best_params}")
    print(f"  Best CV F1: {best_score*100:.2f}%")
    print(f"  Thoi gian: {elapsed:.1f}s ({n_trials} trials)")
    model = XGBClassifier(**best_params, random_state=42, n_jobs=-1,
                           eval_metric='mlogloss', verbosity=0, use_label_encoder=False)
    return model, best_params, best_score, elapsed


# ══════════════════════════════════════════════════════════════════════════════
# SMOTE EXPERIMENT
# ══════════════════════════════════════════════════════════════════════════════

def compare_all_models(all_models, X_test, y_test_enc, le, results_dir):
    print("\n" + "=" * 60)
    print("  TEST SET COMPARISON - Tat ca mo hinh")
    print("=" * 60)

    rows = []
    best_f1 = 0
    best_name = None
    best_model = None

    for name, (model, is_xgb) in all_models.items():
        try:
            y_pred = model.predict(X_test)
            acc = accuracy_score(y_test_enc, y_pred)
            f1_w = f1_score(y_test_enc, y_pred, average='weighted')
            f1_m = f1_score(y_test_enc, y_pred, average='macro')
            prec = precision_score(y_test_enc, y_pred, average='weighted')
            rec = recall_score(y_test_enc, y_pred, average='weighted')
            print(f"  {name:30s} | Acc={acc*100:.2f}% | F1_w={f1_w*100:.2f}%")
            rows.append({'Model': name, 'Accuracy': f'{acc*100:.2f}%',
                         'F1_weighted': f'{f1_w*100:.2f}%', 'F1_macro': f'{f1_m*100:.2f}%',
                         'Precision': f'{prec*100:.2f}%', 'Recall': f'{rec*100:.2f}%',
                         '_acc': acc, '_f1': f1_w})
            if f1_w > best_f1:
                best_f1 = f1_w
                best_name = name
                best_model = model
        except Exception as e:
            print(f"  {name:30s} | LOI: {e}")

    df_compare = pd.DataFrame(rows)
    df_compare = df_compare.sort_values('_f1', ascending=False)
    df_compare = df_compare.drop(columns=['_acc', '_f1'])
    csv_path = os.path.join(results_dir, 'model_comparison.csv')
    df_compare.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"\n[TRAIN] [OK] Da luu bang so sanh tai: {csv_path}")

    return best_name, best_model


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def run_training_pipeline():
    t_total_start = time_module.time()
    print("=" * 70)
    print("  TRAINING PIPELINE - RF & XGBoost")
    print("  + Baseline GridSearchCV")
    print("  + Optuna Bayesian Optimization")
    print("=" * 70)

    results_dir = ensure_results_dir()

    # ── 1. Load data ──────────────────────────────────────────────────────────
    print("\n[STEP 1] Doc du lieu...")
    col = db_connection.get_training_collection()
    docs = list(col.find({}, {'_id': 0}))
    df = pd.DataFrame(docs) if docs else None

    if df is None or len(df) == 0:
        print("  [NOTE] MongoDB training_health_data rong. Thu doc tu CSV...")
        csv_path = settings.CSV_DATA_PATH
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(os.path.dirname(__file__), csv_path)
        if not os.path.exists(csv_path):
            print(f"[FAIL] Khong tim thay file CSV: {csv_path}")
            return False
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.lower()
        if 'label' in df.columns:
            df.rename(columns={'label': 'intended_label'}, inplace=True)
        print(f"  Da doc {len(df)} ban ghi tu CSV: {csv_path}")
    else:
        print(f"  Da doc {len(df)} ban ghi tu MongoDB")
        if 'intended_label' not in df.columns and 'label' in df.columns:
            df.rename(columns={'label': 'intended_label'}, inplace=True)

    if 'intended_label' not in df.columns:
        print("[FAIL] Khong co cot 'intended_label' / 'Label'!")
        return False

    if 'Error' in df['intended_label'].values:
        n_error = (df['intended_label'] == 'Error').sum()
        df = df[df['intended_label'] != 'Error']
        print(f"  Da loc bo {n_error} mau co nhan Error")

    # ── 2. Feature Engineering ────────────────────────────────────────────────
    print("\n[STEP 2] Feature Engineering...")
    df = create_engineered_features(df)

    base_features = ['bpm', 'spo2', 'body_temp', 'gsr_adc']
    eng_features = ['bpm_spo2_ratio', 'temp_gsr_interaction', 'bpm_temp_product',
                    'spo2_gsr_ratio', 'bpm_deviation', 'temp_deviation',
                    'gsr_deviation', 'physiological_stress_index']
    all_features = base_features + eng_features

    n_before = len(df)
    df = df.dropna(subset=base_features + ['intended_label'])
    print(f"  Sau khi dropna: {len(df)} mau (da loai bo {n_before - len(df)} mau NaN/label rong)")

    for col in eng_features:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    X = df[all_features]
    y = df['intended_label']
    print(f"  Features: {len(all_features)} (4 raw + 8 engineered)")
    print(f"  Labels: {dict(y.value_counts())}")

    # ── 3. Visualizations ──────────────────────────────────────────────────────
    print("\n[STEP 3] Tao visualizations...")
    plot_physiological_distributions(df, results_dir)
    plot_correlation_matrix(df, all_features, results_dir)

    # ── 4. Train/Test split ────────────────────────────────────────────────────
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    y_train_enc = le.fit_transform(y_train)
    y_test_enc = le.transform(y_test)

    print(f"  Train: {len(X_train)} | Test: {len(X_test)}")

    # ── 5. All models storage ─────────────────────────────────────────────────
    all_models = {}
    all_cv_results = {}
    all_results = {'n_samples': len(df), 'all_cv_results': all_cv_results}

    # ════════════════════════════════════════════════════════════════════════
    # STAGE A: BASELINE GRIDSEARCHCV
    # ════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  STAGE A: BASELINE GRIDSEARCHCV")
    print(f"  Bat dau luc {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)

    rf_grid, rf_grid_params, rf_grid_cv, rf_grid_time = baseline_gridsearch_rf(X_train, y_train_enc)
    all_models['RF_GridSearchCV'] = (rf_grid, False)
    all_cv_results['RF_GridSearchCV'] = {
        'f1_mean': rf_grid_cv, 'f1_std': 0, 'acc_mean': rf_grid_cv, 'time': rf_grid_time
    }

    xgb_grid, xgb_grid_params, xgb_grid_cv, xgb_grid_time = baseline_gridsearch_xgb(X_train, y_train_enc)
    if xgb_grid is not None:
        all_models['XGB_GridSearchCV'] = (xgb_grid, True)
        all_cv_results['XGB_GridSearchCV'] = {
            'f1_mean': xgb_grid_cv, 'f1_std': 0, 'time': xgb_grid_time
        }

    # ════════════════════════════════════════════════════════════════════════
    # STAGE B: OPTUNA BAYESIAN OPTIMIZATION
    # ════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  STAGE B: OPTUNA BAYESIAN OPTIMIZATION")
    print(f"  Bat dau luc {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)

    rf_opt, rf_opt_params, rf_opt_cv, rf_opt_time = run_optuna_rf(X_train, y_train_enc, n_trials=25)
    if rf_opt is not None:
        rf_opt.fit(X_train, y_train_enc)
        all_models['RF_Optuna'] = (rf_opt, False)
        all_cv_results['RF_Optuna'] = {
            'f1_mean': rf_opt_cv, 'f1_std': 0, 'time': rf_opt_time
        }

    xgb_opt, xgb_opt_params, xgb_opt_cv, xgb_opt_time = run_optuna_xgb(X_train, y_train_enc, n_trials=25)
    if xgb_opt is not None:
        xgb_opt.fit(X_train, y_train_enc)
        all_models['XGB_Optuna'] = (xgb_opt, True)
        all_cv_results['XGB_Optuna'] = {
            'f1_mean': xgb_opt_cv, 'f1_std': 0, 'time': xgb_opt_time
        }

    # ════════════════════════════════════════════════════════════════════════
    # STAGE C: COMPARE MODELS
    # ════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  STAGE C: TEST SET EVALUATION")
    print("=" * 70)

    best_name, best_model = compare_all_models(
        all_models, X_test, y_test_enc, le, results_dir
    )
    print(f"\n  Chon mo hinh tot nhat: {best_name}")

    best_is_xgb = 'XGB' in best_name

    if 'RF_GridSearchCV' in best_name:
        best_params = rf_grid_params
    elif 'XGB_GridSearchCV' in best_name:
        best_params = xgb_grid_params
    elif 'RF_Optuna' in best_name:
        best_params = rf_opt_params
    elif 'XGB_Optuna' in best_name:
        best_params = xgb_opt_params
    else:
        best_params = rf_opt_params if rf_opt_params else rf_grid_params

    y_pred = best_model.predict(X_test)
    accuracy = accuracy_score(y_test_enc, y_pred)
    f1_val = f1_score(y_test_enc, y_pred, average='weighted')

    print(f"\n  BEST MODEL TEST METRICS:")
    print(f"    Accuracy: {accuracy*100:.2f}%")
    print(f"    F1 (weighted): {f1_val*100:.2f}%")
    print(f"\n  Classification Report:")
    print(classification_report(y_test_enc, y_pred, target_names=le.classes_))

    classes = le.classes_
    plot_confusion_matrix(y_test, le.inverse_transform(y_pred), classes, results_dir)

    if hasattr(best_model, 'feature_importances_'):
        plot_feature_importance(best_model, all_features, results_dir)

    plot_cv_comparison(all_cv_results, results_dir)

    # ════════════════════════════════════════════════════════════════════════
    # STAGE D: RETRAIN ON 100% DATA + SAVE
    # ════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  STAGE D: RETRAIN ON 100% DATA + SAVE MODEL")
    print("=" * 70)

    X_full_res = X
    y_full_enc = y_enc

    if best_is_xgb and XGBOOST_AVAILABLE:
        if isinstance(best_params, dict) and 'n_estimators' not in best_params:
            bp = xgb_opt_params if xgb_opt_params else xgb_grid_params
        else:
            bp = best_params
        final = XGBClassifier(**bp, random_state=42, n_jobs=-1,
                               eval_metric='mlogloss', verbosity=0, use_label_encoder=False)
        final.fit(X_full_res, y_full_enc)
        model_data = {
            'model': final,
            'label_encoder': le,
            'model_type': 'xgboost',
            'version': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'features': all_features,
            'trained_on_samples': len(X_full_res),
            'best_params': bp,
            'metrics': {'test_accuracy': accuracy, 'test_f1': f1_val},
        }
    else:
        if isinstance(best_params, dict) and 'n_estimators' not in best_params:
            bp = rf_opt_params if rf_opt_params else rf_grid_params
        else:
            bp = best_params
        final = RandomForestClassifier(**bp, random_state=42, n_jobs=-1)
        final.fit(X_full_res, y_full_enc)
        model_data = {
            'model': final,
            'label_encoder': le,
            'model_type': 'randomforest',
            'version': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'features': all_features,
            'trained_on_samples': len(X_full_res),
            'best_params': bp,
            'metrics': {'test_accuracy': accuracy, 'test_f1': f1_val},
        }

    os.makedirs(os.path.dirname(settings.ML_MODEL_PATH), exist_ok=True)
    joblib.dump(model_data, settings.ML_MODEL_PATH)
    print(f"  Da luu mo hinh tai: {settings.ML_MODEL_PATH}")
    print(f"  Model type: {model_data['model_type']}")

    # ── Summary ─────────────────────────────────────────────────────────────
    t_total = time_module.time() - t_total_start

    print("\n" + "=" * 70)
    print("  TOM TAT")
    print("=" * 70)
    print(f"  Mo hinh chon: {best_name}")
    print(f"  Test Accuracy: {accuracy*100:.2f}%")
    print(f"  Test F1 (weighted): {f1_val*100:.2f}%")
    print(f"  Features: {len(all_features)}")
    print(f"  Tong thoi gian: {t_total:.1f}s")
    print(f"  Ket qua luu tai: {results_dir}")
    print(f"  Model luu tai: {settings.ML_MODEL_PATH}")
    print("=" * 70)
    print("  HOAN TAT!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    run_training_pipeline()

