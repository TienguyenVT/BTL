# -*- coding: utf-8 -*-
"""
Script Huấn luyện Mô hình Machine Learning (Random Forest + XGBoost).

Quy trình MỚI:
  1. Đọc dữ liệu từ MongoDB (collection: training_health_data)
  2. Feature Engineering (tạo thêm derived features)
  3. Train và so sánh RandomForest vs XGBoost
  4. Cross-validation + Hyperparameter Tuning
  5. Đánh giá và trực quan hóa
  6. Lưu model thành file .pkl

Giai đoạn cải thiện:
  - Cross-validation với StratifiedKFold
  - Hyperparameter Tuning với GridSearchCV
  - Feature Engineering
  - XGBoost comparison
"""

import os
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score

# Thử import XGBoost - nếu không có thì bỏ qua phần so sánh
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("[TRAIN] ⚠ XGBoost không được cài đặt. Sẽ bỏ qua so sánh XGBoost.")

from config import settings
from database import db_connection


def ensure_results_dir():
    """Đảm bảo thư mục lưu kết quả tồn tại."""
    results_dir = os.path.join(os.path.dirname(__file__), 'result')
    os.makedirs(results_dir, exist_ok=True)
    return results_dir


def save_physiological_distributions(df: pd.DataFrame, results_dir: str):
    """Vẽ và lưu đồ thị phân bổ các chỉ số sinh lý."""
    print("[TRAIN] [VISUALIZATION] Đang vẽ đồ thị phân bố các chỉ số sinh lý...")
    fig, axes = plt.subplots(1, 4, figsize=(20, 6))
    fig.suptitle('Phân bố các chỉ số sinh lý theo trạng thái sức khỏe (Training Data)', fontsize=16, fontweight='bold')

    sns.boxplot(ax=axes[0], x='label', y='bpm', data=df, hue='label', legend=False, palette='Set2')
    axes[0].set_title('Nhịp tim (BPM)')

    sns.boxplot(ax=axes[1], x='label', y='gsr_adc', data=df, hue='label', legend=False, palette='Set2')
    axes[1].set_title('Điện trở da (GSR_ADC)')

    sns.boxplot(ax=axes[2], x='label', y='body_temp', data=df, hue='label', legend=False, palette='Set2')
    axes[2].set_title('Nhiệt độ cơ thể (Body_Temp)')

    sns.boxplot(ax=axes[3], x='label', y='spo2', data=df, hue='label', legend=False, palette='Set2')
    axes[3].set_title('SpO2')

    plt.tight_layout()
    plt_path = os.path.join(results_dir, 'physiological_distributions.png')
    plt.savefig(plt_path)
    plt.close()
    print(f"[TRAIN] [VISUALIZATION] ✓ Đã lưu tại: {plt_path}")


def save_correlation_matrix(df: pd.DataFrame, results_dir: str):
    """Vẽ và lưu ma trận tương quan."""
    print("[TRAIN] [VISUALIZATION] Đang vẽ ma trận tương quan...")
    plt.figure(figsize=(8, 6))
    cols_for_corr = ['ext_temp_c', 'ext_humidity_pct', 'body_temp', 'gsr_adc', 'bpm', 'spo2']
    
    # Chỉ lấy các cột số học có trong dataframe
    available_cols = [c for c in cols_for_corr if c in df.columns]
    corr_matrix = df[available_cols].corr(method='pearson')

    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=.5, square=True, vmin=-1, vmax=1)
    plt.title('Ma trận tương quan Pearson', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt_path = os.path.join(results_dir, 'correlation_matrix.png')
    plt.savefig(plt_path)
    plt.close()
    print(f"[TRAIN] [VISUALIZATION] ✓ Đã lưu tại: {plt_path}")


def save_confusion_matrix(y_true, y_pred, classes, results_dir: str):
    """Vẽ và lưu ma trận nhầm lẫn."""
    print("[TRAIN] [VISUALIZATION] Đang vẽ ma trận nhầm lẫn...")
    plt.figure(figsize=(8, 6))
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=classes, yticklabels=classes)
    plt.title('Ma trận nhầm lẫn (Confusion Matrix)', fontsize=14, fontweight='bold')
    plt.xlabel('Nhãn dự đoán')
    plt.ylabel('Nhãn thực tế')
    plt.tight_layout()
    plt_path = os.path.join(results_dir, 'confusion_matrix.png')
    plt.savefig(plt_path)
    plt.close()
    print(f"[TRAIN] [VISUALIZATION] ✓ Đã lưu tại: {plt_path}")


def save_feature_importance(model, feature_names, results_dir: str):
    """Vẽ và lưu độ quan trọng của đặc trưng."""
    print("[TRAIN] [VISUALIZATION] Đang vẽ độ quan trọng của đặc trưng...")
    plt.figure(figsize=(10, 6))
    feature_importances = pd.Series(model.feature_importances_, index=feature_names).sort_values(ascending=False)

    sns.barplot(x=feature_importances.values, y=feature_importances.index, hue=feature_importances.index, palette='viridis', legend=False)
    plt.title('Mức độ quan trọng của các đặc trưng (Feature Importance)', fontsize=14, fontweight='bold')
    plt.xlabel('Điểm quan trọng')
    plt.ylabel('Đặc trưng')
    plt.tight_layout()
    plt_path = os.path.join(results_dir, 'feature_importance.png')
    plt.savefig(plt_path)
    plt.close()
    print(f"[TRAIN] [VISUALIZATION] ✓ Đã lưu tại: {plt_path}")


def perform_cross_validation(X, y, model, cv_folds: int = 5):
    """
    Thực hiện Stratified K-Fold Cross-Validation.
    
    Args:
        X: Feature matrix
        y: Labels
        model: Classifier instance
        cv_folds: Số lượng folds (mặc định 5)
    
    Returns:
        Dictionary chứa các metrics
    """
    print("\n" + "=" * 60)
    print("  CROSS-VALIDATION (Stratified K-Fold)")
    print("=" * 60)
    
    # Sử dụng StratifiedKFold để đảm bảo tỷ lệ class được giữ nguyên trong mỗi fold
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
    
    # Accuracy cross-validation
    cv_scores_accuracy = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
    
    # F1-Score (weighted) - cân bằng precision/recall cho multi-class
    cv_scores_f1 = cross_val_score(model, X, y, cv=cv, scoring='f1_weighted')
    
    # F1-Score (macro) - trung bình cộng của F1 mỗi class
    cv_scores_f1_macro = cross_val_score(model, X, y, cv=cv, scoring='f1_macro')
    
    # Precision
    cv_scores_precision = cross_val_score(model, X, y, cv=cv, scoring='precision_weighted')
    
    # Recall
    cv_scores_recall = cross_val_score(model, X, y, cv=cv, scoring='recall_weighted')
    
    results = {
        'accuracy': {
            'mean': cv_scores_accuracy.mean(),
            'std': cv_scores_accuracy.std(),
            'scores': cv_scores_accuracy,
            'ci95': 1.96 * cv_scores_accuracy.std()
        },
        'f1_weighted': {
            'mean': cv_scores_f1.mean(),
            'std': cv_scores_f1.std(),
            'scores': cv_scores_f1,
            'ci95': 1.96 * cv_scores_f1.std()
        },
        'f1_macro': {
            'mean': cv_scores_f1_macro.mean(),
            'std': cv_scores_f1_macro.std(),
            'scores': cv_scores_f1_macro,
            'ci95': 1.96 * cv_scores_f1_macro.std()
        },
        'precision_weighted': {
            'mean': cv_scores_precision.mean(),
            'std': cv_scores_precision.std(),
            'scores': cv_scores_precision,
            'ci95': 1.96 * cv_scores_precision.std()
        },
        'recall_weighted': {
            'mean': cv_scores_recall.mean(),
            'std': cv_scores_recall.std(),
            'scores': cv_scores_recall,
            'ci95': 1.96 * cv_scores_recall.std()
        }
    }
    
    print(f"\n  📊 Kết quả Cross-Validation ({cv_folds}-Fold):")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Accuracy:    {results['accuracy']['mean']*100:.2f}% (+/- {results['accuracy']['ci95']*100:.2f}%)")
    print(f"  F1 (weighted): {results['f1_weighted']['mean']*100:.2f}% (+/- {results['f1_weighted']['ci95']*100:.2f}%)")
    print(f"  F1 (macro):    {results['f1_macro']['mean']*100:.2f}% (+/- {results['f1_macro']['ci95']*100:.2f}%)")
    print(f"  Precision:   {results['precision_weighted']['mean']*100:.2f}% (+/- {results['precision_weighted']['ci95']*100:.2f}%)")
    print(f"  Recall:      {results['recall_weighted']['mean']*100:.2f}% (+/- {results['recall_weighted']['ci95']*100:.2f}%)")
    print(f"\n  📈 Chi tiết từng Fold:")
    for i, (acc, f1) in enumerate(zip(cv_scores_accuracy, cv_scores_f1), 1):
        print(f"      Fold {i}: Accuracy={acc*100:.2f}% | F1={f1*100:.2f}%")
    
    return results


def perform_hyperparameter_tuning(X_train, y_train, cv_folds: int = 3):
    """
    Thực hiện Hyperparameter Tuning với GridSearchCV.
    
    Args:
        X_train: Feature matrix cho training
        y_train: Labels cho training
        cv_folds: Số folds cho GridSearchCV (mặc định 3 để tiết kiệm thời gian)
    
    Returns:
        Tuple (best_model, best_params, best_cv_score)
    """
    print("\n" + "=" * 60)
    print("  HYPERPARAMETER TUNING (GridSearchCV)")
    print("=" * 60)
    
    # Định nghĩa parameter grid cho RandomForest
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [10, 20, None],  # None = unlimited
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
        'class_weight': [None, 'balanced']  # Xử lý class imbalance
    }
    
    # Khởi tạo base model
    base_model = RandomForestClassifier(random_state=42, n_jobs=-1)
    
    # GridSearchCV với 3-fold CV (giảm thời gian tính toán)
    # Sử dụng f1_weighted vì dataset có class imbalance
    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=param_grid,
        cv=cv_folds,
        scoring='f1_weighted',
        n_jobs=-1,
        verbose=2,
        refit=True  # Refit model với best params
    )
    
    print(f"\n  🔍 Đang tìm kiếm {len(param_grid['n_estimators']) * len(param_grid['max_depth']) * len(param_grid['min_samples_split']) * len(param_grid['min_samples_leaf']) * len(param_grid['class_weight'])} combinations...")
    print(f"     (CV={cv_folds} folds)")
    
    grid_search.fit(X_train, y_train)
    
    print(f"\n  ✅ Hoàn tất GridSearchCV!")
    print(f"\n  📋 Best Parameters:")
    for param, value in grid_search.best_params_.items():
        print(f"      {param}: {value}")
    print(f"\n  📊 Best CV Score (F1-weighted): {grid_search.best_score_*100:.2f}%")
    
    return grid_search.best_estimator_, grid_search.best_params_, grid_search.best_score_


def compare_with_xgboost(X_train, y_train, X_test, y_test_original, best_rf_params: dict, results_dir: str):
    """
    So sánh RandomForest (best params từ GridSearch) với XGBoost.

    Args:
        X_train, y_train: Training data
        X_test: Test features
        y_test_original: Test labels (gốc - string labels)
        best_rf_params: Best parameters đã tìm được từ RF GridSearch
        results_dir: Thư mục lưu kết quả

    Returns:
        Dictionary chứa kết quả so sánh
    """
    if not XGBOOST_AVAILABLE:
        print("\n" + "=" * 60)
        print("  XGBOOST COMPARISON - SKIPPED (XGBoost not installed)")
        print("=" * 60)
        return None

    print("\n" + "=" * 60)
    print("  XGBOOST COMPARISON")
    print("=" * 60)

    # Chuẩn bị labels cho XGBoost (cần integer labels)
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    y_train_encoded = le.fit_transform(y_train)
    y_test_encoded = le.transform(y_test_original)

    # XGBoost với default params (nhanh)
    print("\n  🔄 Training XGBoost (default params)...")
    xgb_model = XGBClassifier(
        n_estimators=200,
        max_depth=10,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1,
        eval_metric='mlogloss'
    )
    xgb_model.fit(X_train, y_train_encoded)

    # Đánh giá XGBoost
    xgb_pred_encoded = xgb_model.predict(X_test)
    xgb_accuracy = accuracy_score(y_test_encoded, xgb_pred_encoded) * 100
    xgb_f1 = f1_score(y_test_encoded, xgb_pred_encoded, average='weighted') * 100

    print(f"\n  📊 XGBoost Results:")
    print(f"      Accuracy: {xgb_accuracy:.2f}%")
    print(f"      F1-Score (weighted): {xgb_f1:.2f}%")

    # So sánh với RF (đã train ở trên)
    rf_model = RandomForestClassifier(**best_rf_params, random_state=42, n_jobs=-1)
    rf_model.fit(X_train, y_train)
    rf_pred = rf_model.predict(X_test)
    rf_accuracy = accuracy_score(y_test_original, rf_pred) * 100
    rf_f1 = f1_score(y_test_original, rf_pred, average='weighted') * 100

    print(f"\n  📊 RandomForest Results (best params):")
    print(f"      Accuracy: {rf_accuracy:.2f}%")
    print(f"      F1-Score (weighted): {rf_f1:.2f}%")

    # Quyết định chọn model nào
    if xgb_f1 > rf_f1:
        print(f"\n  🏆 XGBoost selected (F1: {xgb_f1:.2f}% > {rf_f1:.2f}%)")
        best_model = xgb_model
        best_model_type = 'xgboost'
        best_accuracy = xgb_accuracy
        best_f1 = xgb_f1
    else:
        print(f"\n  🏆 RandomForest selected (F1: {rf_f1:.2f}% >= {xgb_f1:.2f}%)")
        best_model = rf_model
        best_model_type = 'randomforest'
        best_accuracy = rf_accuracy
        best_f1 = rf_f1

    # Lưu kết quả so sánh
    comparison_path = os.path.join(results_dir, 'model_comparison_results.txt')
    with open(comparison_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("MODEL COMPARISON: RandomForest vs XGBoost\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"RandomForest (best params from GridSearch):\n")
        f.write(f"  - Accuracy: {rf_accuracy:.2f}%\n")
        f.write(f"  - F1-Score (weighted): {rf_f1:.2f}%\n\n")
        f.write(f"XGBoost (default params):\n")
        f.write(f"  - Accuracy: {xgb_accuracy:.2f}%\n")
        f.write(f"  - F1-Score (weighted): {xgb_f1:.2f}%\n\n")
        f.write(f"Selected Model: {best_model_type}\n")
        f.write(f"Final Accuracy: {best_accuracy:.2f}%\n")
        f.write(f"Final F1-Score: {best_f1:.2f}%\n")

    print(f"\n[TRAIN] [VISUALIZATION] ✓ Đã lưu tại: {comparison_path}")

    return {
        'best_model': best_model,
        'best_model_type': best_model_type,
        'rf_accuracy': rf_accuracy,
        'rf_f1': rf_f1,
        'xgb_accuracy': xgb_accuracy,
        'xgb_f1': xgb_f1,
        'best_accuracy': best_accuracy,
        'best_f1': best_f1,
        'label_encoder': le
    }


def save_cv_results(cv_results, results_dir: str):
    """Lưu kết quả cross-validation thành file text."""
    print("[TRAIN] [VISUALIZATION] Đang lưu kết quả Cross-Validation...")
    
    cv_path = os.path.join(results_dir, 'cross_validation_results.txt')
    
    with open(cv_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("CROSS-VALIDATION RESULTS (5-Fold Stratified)\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"Accuracy (mean ± std): {cv_results['accuracy']['mean']*100:.2f}% ± {cv_results['accuracy']['std']*100:.2f}%\n")
        f.write(f"F1-Score Weighted (mean ± std): {cv_results['f1_weighted']['mean']*100:.2f}% ± {cv_results['f1_weighted']['std']*100:.2f}%\n")
        f.write(f"F1-Score Macro (mean ± std): {cv_results['f1_macro']['mean']*100:.2f}% ± {cv_results['f1_macro']['std']*100:.2f}%\n")
        f.write(f"Precision (mean ± std): {cv_results['precision_weighted']['mean']*100:.2f}% ± {cv_results['precision_weighted']['std']*100:.2f}%\n")
        f.write(f"Recall (mean ± std): {cv_results['recall_weighted']['mean']*100:.2f}% ± {cv_results['recall_weighted']['std']*100:.2f}%\n\n")
        
        f.write("Fold-by-Fold Details:\n")
        f.write("-" * 40 + "\n")
        for i, (acc, f1) in enumerate(zip(cv_results['accuracy']['scores'], cv_results['f1_weighted']['scores']), 1):
            f.write(f"Fold {i}: Accuracy={acc*100:.2f}% | F1={f1*100:.2f}%\n")
    
    print(f"[TRAIN] [VISUALIZATION] ✓ Đã lưu tại: {cv_path}")


def save_tuning_results(best_params, best_score, results_dir: str):
    """Lưu kết quả hyperparameter tuning thành file text."""
    print("[TRAIN] [VISUALIZATION] Đang lưu kết quả Hyperparameter Tuning...")
    
    tuning_path = os.path.join(results_dir, 'hyperparameter_tuning_results.txt')
    
    with open(tuning_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("HYPERPARAMETER TUNING RESULTS\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("Best Parameters:\n")
        f.write("-" * 40 + "\n")
        for param, value in best_params.items():
            f.write(f"  {param}: {value}\n")
        
        f.write(f"\nBest CV Score (F1-weighted): {best_score*100:.2f}%\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("Parameter Grid Searched:\n")
        f.write("-" * 40 + "\n")
        f.write("  n_estimators: [100, 200, 300]\n")
        f.write("  max_depth: [10, 20, None]\n")
        f.write("  min_samples_split: [2, 5, 10]\n")
        f.write("  min_samples_leaf: [1, 2, 4]\n")
        f.write("  class_weight: [None, 'balanced']\n")
    
    print(f"[TRAIN] [VISUALIZATION] ✓ Đã lưu tại: {tuning_path}")


def create_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo thêm các engineered features để cải thiện model performance.

    Features được tạo:
    - bpm_spo2_ratio: Tỷ lệ BPM/SPO2
    - temp_gsr_interaction: Tương tác nhiệt độ và GSR
    - bpm_temp_product: Tích BPM và nhiệt độ
    - spo2_gsr_ratio: Tỷ lệ SpO2/GSR
    - bpm_deviation: Độ lệch BPM so với trung bình Normal (75)
    - temp_deviation: Độ lệch nhiệt độ so với trung bình Normal (36.8)
    - gsr_deviation: Độ lệch GSR so với trung bình Normal (2200)
    - physiological_stress_index: Chỉ số stress tổng hợp

    Args:
        df: DataFrame gốc với các cột ['bpm', 'spo2', 'body_temp', 'gsr_adc']

    Returns:
        DataFrame với các features mới
    """
    print("[TRAIN] [FEATURE ENGINEERING] Đang tạo engineered features...")

    df_engineered = df.copy()

    # Tỷ lệ BPM/SPO2 - có thể giúp phân biệt stress vs normal
    df_engineered['bpm_spo2_ratio'] = df_engineered['bpm'] / (df_engineered['spo2'] + 1e-6)

    # Tương tác nhiệt độ và GSR - fever có xu hướng nhiệt cao nhưng GSR bình thường
    df_engineered['temp_gsr_interaction'] = df_engineered['body_temp'] * df_engineered['gsr_adc'] / 1000

    # Tích BPM và nhiệt độ
    df_engineered['bpm_temp_product'] = df_engineered['bpm'] * df_engineered['body_temp']

    # Tỷ lệ SpO2/GSR
    df_engineered['spo2_gsr_ratio'] = df_engineered['spo2'] / (df_engineered['gsr_adc'] + 1e-6)

    # Độ lệch BPM so với baseline Normal (~75)
    df_engineered['bpm_deviation'] = abs(df_engineered['bpm'] - 75)

    # Độ lệch nhiệt độ so với baseline Normal (~36.8)
    df_engineered['temp_deviation'] = abs(df_engineered['body_temp'] - 36.8)

    # Độ lệch GSR so với baseline Normal (~2200)
    df_engineered['gsr_deviation'] = abs(df_engineered['gsr_adc'] - 2200)

    # Chỉ số stress tổng hợp: BPM cao + GSR cao + SpO2 bình thường/tăng nhẹ
    df_engineered['physiological_stress_index'] = (
        (df_engineered['bpm'] - 75) / 75 +  # Normalized BPM deviation
        (df_engineered['gsr_adc'] - 2200) / 2200  # Normalized GSR deviation
    )

    new_features = [
        'bpm_spo2_ratio', 'temp_gsr_interaction', 'bpm_temp_product',
        'spo2_gsr_ratio', 'bpm_deviation', 'temp_deviation',
        'gsr_deviation', 'physiological_stress_index'
    ]

    print(f"[TRAIN] [FEATURE ENGINEERING] ✓ Đã tạo {len(new_features)} features mới")
    print(f"    Features: {', '.join(new_features)}")

    return df_engineered


def run_training_pipeline():
    """Hàm chạy toàn bộ quy trình đọc dữ liệu từ DB và huấn luyện mô hình."""
    print("=" * 60)
    print("  BẮT ĐẦU QUY TRÌNH HUẤN LUYỆN MÔ HÌNH (TRAINING WORKFLOW)")
    print("  + Giai đoạn 1: Cross-Validation & Hyperparameter Tuning")
    print("=" * 60)

    # Tạo thư mục lưu kết quả 
    results_dir = ensure_results_dir()

    # 1. Đọc dữ liệu từ DB (Collection: training_health_data)
    print(f"[TRAIN] [START] Đang đọc dữ liệu từ MongoDB: collection '{settings.TRAINING_COLLECTION}'...")
    training_collection = db_connection.get_training_collection()
    
    docs = list(training_collection.find({}, {'_id': 0}))
    
    if not docs:
        print("[TRAIN] [FAIL] Không tìm thấy bản ghi nào trong Database!")
        return False
        
    print(f"[TRAIN] [OK] Đã lấy {len(docs)} bản ghi từ Database.")

    # 2. Chuẩn bị dữ liệu và Trực quan hóa 
    print("[TRAIN] [START] Đang chuẩn bị dữ liệu cho Machine Learning...")
    
    df_train = pd.DataFrame(docs)
    
    if 'label' not in df_train.columns:
        print("[TRAIN] [FAIL] Dữ liệu trong DB không có cột 'label' để huấn luyện!")
        return False

    # Lưu hình ảnh 1: Phân bổ dữ liệu
    save_physiological_distributions(df_train, results_dir)
    
    # Lưu hình ảnh 2: Ma trận tương quan
    save_correlation_matrix(df_train, results_dir)

    # ================================================================
    # FEATURE ENGINEERING
    # ================================================================
    # Tạo thêm các engineered features
    df_train = create_engineered_features(df_train)

    # Chọn các Feature để học (bao gồm cả engineered features)
    base_features = ['bpm', 'spo2', 'body_temp', 'gsr_adc']
    engineered_features = [
        'bpm_spo2_ratio', 'temp_gsr_interaction', 'bpm_temp_product',
        'spo2_gsr_ratio', 'bpm_deviation', 'temp_deviation',
        'gsr_deviation', 'physiological_stress_index'
    ]
    features = base_features + engineered_features
    X = df_train[features]
    y = df_train['label']

    print(f"[TRAIN] Tổng số features: {len(features)} (4 cơ bản + 8 engineered)")

    # ================================================================
    # GIAI ĐOẠN 1: CROSS-VALIDATION (Trước khi tuning)
    # ================================================================
    # Trước tiên, chạy CV với default model để có baseline
    base_rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    cv_results_baseline = perform_cross_validation(X, y, base_rf, cv_folds=5)
    save_cv_results(cv_results_baseline, results_dir)

    # ================================================================
    # GIAI ĐOẠN 1: HYPERPARAMETER TUNING
    # ================================================================
    # Split data để tuning (sử dụng train set, không dùng test set để tránh data leakage)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"[TRAIN] Dataset: Train={len(X_train)} | Test={len(X_test)}")
    
    # Chạy GridSearchCV để tìm best hyperparameters
    best_model, best_params, best_cv_score = perform_hyperparameter_tuning(X_train, y_train, cv_folds=3)
    save_tuning_results(best_params, best_cv_score, results_dir)

    # ================================================================
    # XGBOOST COMPARISON
    # ================================================================
    comparison_results = compare_with_xgboost(
        X_train, y_train, X_test, y_test, best_params, results_dir
    )

    # ================================================================
    # ĐÁNH GIÁ TRÊN TẬP TEST VỚI BEST MODEL
    # ================================================================
    print("\n" + "=" * 60)
    print("  ĐÁNH GIÁ TRÊN TẬP TEST")
    print("=" * 60)

    if comparison_results:
        # Sử dụng model tốt nhất từ comparison
        if comparison_results['best_model_type'] == 'xgboost':
            # XGBoost: predict trên X_test (đã có engineered features)
            y_pred_encoded = comparison_results['best_model'].predict(X_test)
            y_pred = comparison_results['label_encoder'].inverse_transform(y_pred_encoded)
            classes = comparison_results['label_encoder'].classes_
        else:
            y_pred = comparison_results['best_model'].predict(X_test)
            classes = comparison_results['best_model'].classes_

        accuracy = comparison_results['best_accuracy']
        f1 = comparison_results['best_f1']

        print(f"[TRAIN] Selected Model: {comparison_results['best_model_type']}")
        print(f"[TRAIN] Test Accuracy: {accuracy:.2f}%")
        print(f"[TRAIN] Test F1-Score (weighted): {f1:.2f}%")
    else:
        # Fallback to RF only
        y_pred = best_model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred) * 100
        f1 = f1_score(y_test, y_pred, average='weighted') * 100
        classes = best_model.classes_
        comparison_results = {'best_model_type': 'randomforest'}

    print("\n[TRAIN] Classification Report:")
    # Define classes for classification_report
    if comparison_results and comparison_results.get('best_model_type') == 'xgboost':
        classes = comparison_results['label_encoder'].classes_
    else:
        classes = best_model.classes_

    print(classification_report(y_test, y_pred, labels=classes))

    # Lưu hình ảnh 3: Ma trận nhầm lẫn
    save_confusion_matrix(y_test, y_pred, classes, results_dir)

    # Lưu hình ảnh 4: Mức độ quan trọng của đặc trưng
    # Sử dụng model được chọn (RF hoặc XGBoost)
    if comparison_results and comparison_results.get('best_model_type') == 'xgboost':
        model_for_importance = comparison_results['best_model']
    else:
        model_for_importance = best_model
    save_feature_importance(model_for_importance, features, results_dir)

    # ================================================================
    # RETRAIN TRÊN TOÀN BỘ DỮ LIỆU VỚI BEST PARAMS
    # ================================================================
    print("\n[TRAIN] [START] Bắt đầu huấn luyện lại mô hình trên toàn bộ 100% dữ liệu...")

    # Tạo final model với best params đã tìm được
    if comparison_results and comparison_results.get('best_model_type') == 'xgboost':
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        y_encoded = le.fit_transform(y)
        final_model = XGBClassifier(
            n_estimators=200,
            max_depth=10,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
            eval_metric='mlogloss'
        )
        final_model.fit(X, y_encoded)

        # Lưu kèm metadata để version tracking
        model_data = {
            'model': final_model,
            'label_encoder': le,
            'model_type': 'xgboost',
            'version': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'features': features,
            'trained_on_samples': len(X),
            'metrics': {
                'test_accuracy': accuracy,
                'test_f1': f1
            }
        }
        joblib.dump(model_data, settings.ML_MODEL_PATH)
    else:
        final_model = RandomForestClassifier(**best_params, random_state=42, n_jobs=-1)
        final_model.fit(X, y)

        # Lưu kèm metadata để version tracking
        model_data = {
            'model': final_model,
            'model_type': 'randomforest',
            'version': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'features': features,
            'trained_on_samples': len(X),
            'best_params': best_params,
            'metrics': {
                'test_accuracy': accuracy,
                'test_f1': f1
            }
        }
        joblib.dump(model_data, settings.ML_MODEL_PATH)

    print(f"[TRAIN] [OK] Đã huấn luyện xong với tổng cộng {len(X)} mẫu dữ liệu.")
    print(f"[TRAIN] [OK] Đã lưu mô hình tại: {settings.ML_MODEL_PATH}")

    # ================================================================
    # TỔNG KẾT
    # ================================================================
    print("\n" + "=" * 60)
    print("  TỔNG KẾT GIAI ĐOẠN 2")
    print("=" * 60)
    print(f"  📊 Baseline (default params) CV Accuracy: {cv_results_baseline['accuracy']['mean']*100:.2f}%")
    print(f"  📊 Best Model CV F1-Score: {best_cv_score*100:.2f}%")
    print(f"  📊 Selected Model: {comparison_results.get('best_model_type', 'randomforest')}")
    print(f"  📊 Test Accuracy: {accuracy:.2f}%")
    print(f"  📊 Test F1-Score: {f1:.2f}%")
    print(f"\n  🔧 Features: {len(features)} (4 base + 8 engineered)")
    print(f"  ⚙️  Best Parameters:")
    for param, value in best_params.items():
        print(f"      {param}: {value}")

    print("\n  📁 Kết quả đã lưu tại:", results_dir)
    print("=" * 60)
    print("  HOÀN TẤT GIAI ĐOẠN 2!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    run_training_pipeline()
