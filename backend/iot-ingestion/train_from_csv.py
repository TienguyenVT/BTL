# -*- coding: utf-8 -*-
"""
Script huấn luyện ML với CSV data.
Chạy Cross-Validation và Hyperparameter Tuning.

Sử dụng: python train_from_csv.py
"""

import os
import sys
import pandas as pd
import joblib
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import (
    train_test_split, cross_val_score, StratifiedKFold, GridSearchCV
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score, f1_score
)

# Cấu hình đường dẫn
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "..", "Data", "health_data_all.csv")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "result")
MODEL_PATH = os.path.join(SCRIPT_DIR, "ml_model", "random_forest.pkl")


def ensure_dirs():
    """Tạo thư mục nếu chưa tồn tại."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)


def load_and_preprocess_data(csv_path: str) -> pd.DataFrame:
    """Load và tiền xử lý dữ liệu từ CSV."""
    print(f"\n[DATA] Đang đọc dữ liệu từ: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"[DATA] Tổng số bản ghi: {len(df)}")
    print(f"[DATA] Các cột: {list(df.columns)}")
    
    # Lọc bỏ các nhãn Error (nếu có)
    if 'Label' in df.columns:
        df = df[df['Label'] != 'Error']
        print(f"[DATA] Sau khi lọc Error: {len(df)} bản ghi")
    
    # Kiểm tra phân bố nhãn
    print(f"\n[DATA] Phân bố nhãn:")
    print(df['Label'].value_counts())
    
    return df


def perform_cross_validation(X, y, model, cv_folds: int = 5):
    """Thực hiện Stratified K-Fold Cross-Validation."""
    print("\n" + "=" * 60)
    print("  CROSS-VALIDATION (5-Fold Stratified)")
    print("=" * 60)
    
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
    
    cv_scores_accuracy = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
    cv_scores_f1 = cross_val_score(model, X, y, cv=cv, scoring='f1_weighted')
    cv_scores_f1_macro = cross_val_score(model, X, y, cv=cv, scoring='f1_macro')
    cv_scores_precision = cross_val_score(model, X, y, cv=cv, scoring='precision_weighted')
    cv_scores_recall = cross_val_score(model, X, y, cv=cv, scoring='recall_weighted')
    
    results = {
        'accuracy': {'mean': cv_scores_accuracy.mean(), 'std': cv_scores_accuracy.std()},
        'f1_weighted': {'mean': cv_scores_f1.mean(), 'std': cv_scores_f1.std()},
        'f1_macro': {'mean': cv_scores_f1_macro.mean(), 'std': cv_scores_f1_macro.std()},
        'precision': {'mean': cv_scores_precision.mean(), 'std': cv_scores_precision.std()},
        'recall': {'mean': cv_scores_recall.mean(), 'std': cv_scores_recall.std()}
    }
    
    print(f"\n  📊 Kết quả Cross-Validation ({cv_folds}-Fold):")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Accuracy:    {results['accuracy']['mean']*100:.2f}% (+/- {results['accuracy']['std']*100*1.96:.2f}%)")
    print(f"  F1 (weighted): {results['f1_weighted']['mean']*100:.2f}% (+/- {results['f1_weighted']['std']*100*1.96:.2f}%)")
    print(f"  F1 (macro):    {results['f1_macro']['mean']*100:.2f}% (+/- {results['f1_macro']['std']*100*1.96:.2f}%)")
    print(f"  Precision:   {results['precision']['mean']*100:.2f}% (+/- {results['precision']['std']*100*1.96:.2f}%)")
    print(f"  Recall:      {results['recall']['mean']*100:.2f}% (+/- {results['recall']['std']*100*1.96:.2f}%)")
    
    print(f"\n  📈 Chi tiết từng Fold:")
    for i, (acc, f1) in enumerate(zip(cv_scores_accuracy, cv_scores_f1), 1):
        print(f"      Fold {i}: Accuracy={acc*100:.2f}% | F1={f1*100:.2f}%")
    
    return results


def perform_hyperparameter_tuning(X_train, y_train, cv_folds: int = 3):
    """Thực hiện Hyperparameter Tuning với GridSearchCV."""
    print("\n" + "=" * 60)
    print("  HYPERPARAMETER TUNING (GridSearchCV)")
    print("=" * 60)
    
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [10, 20, None],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
        'class_weight': [None, 'balanced']
    }
    
    base_model = RandomForestClassifier(random_state=42, n_jobs=-1)
    
    total_combinations = (len(param_grid['n_estimators']) * len(param_grid['max_depth']) * 
                        len(param_grid['min_samples_split']) * len(param_grid['min_samples_leaf']) * 
                        len(param_grid['class_weight']))
    
    print(f"\n  🔍 Đang tìm kiếm {total_combinations} combinations...")
    print(f"     (CV={cv_folds} folds, scoring=f1_weighted)")
    
    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=param_grid,
        cv=cv_folds,
        scoring='f1_weighted',
        n_jobs=-1,
        verbose=1
    )
    
    grid_search.fit(X_train, y_train)
    
    print(f"\n  ✅ Hoàn tất GridSearchCV!")
    print(f"\n  📋 Best Parameters:")
    for param, value in grid_search.best_params_.items():
        print(f"      {param}: {value}")
    print(f"\n  📊 Best CV Score (F1-weighted): {grid_search.best_score_*100:.2f}%")
    
    return grid_search.best_estimator_, grid_search.best_params_, grid_search.best_score_


def save_visualizations(y_test, y_pred, classes, model, X, results_dir):
    """Lưu các biểu đồ visualization."""
    
    # 1. Confusion Matrix
    print("[VISUAL] Đang vẽ Confusion Matrix...")
    plt.figure(figsize=(8, 6))
    cm = confusion_matrix(y_test, y_pred, labels=classes)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=classes, yticklabels=classes)
    plt.title('Ma trận nhầm lẫn (Confusion Matrix)', fontsize=14, fontweight='bold')
    plt.xlabel('Nhãn dự đoán')
    plt.ylabel('Nhãn thực tế')
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'confusion_matrix.png'), dpi=150)
    plt.close()
    
    # 2. Feature Importance
    print("[VISUAL] Đang vẽ Feature Importance...")
    plt.figure(figsize=(10, 6))
    feature_importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    sns.barplot(x=feature_importances.values, y=feature_importances.index, palette='viridis')
    plt.title('Mức độ quan trọng của các đặc trưng (Feature Importance)', fontsize=14, fontweight='bold')
    plt.xlabel('Điểm quan trọng')
    plt.ylabel('Đặc trưng')
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'feature_importance.png'), dpi=150)
    plt.close()
    
    # 3. Label Distribution
    print("[VISUAL] Đang vẽ Label Distribution...")
    plt.figure(figsize=(8, 6))
    label_counts = pd.Series(y_test).value_counts()
    sns.barplot(x=label_counts.index, y=label_counts.values, palette='Set2')
    plt.title('Phân bố nhãn trong tập Test', fontsize=14, fontweight='bold')
    plt.xlabel('Nhãn')
    plt.ylabel('Số lượng')
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'label_distribution.png'), dpi=150)
    plt.close()


def save_results_to_file(cv_results, tuning_results, test_results, best_params, results_dir):
    """Lưu kết quả ra file text."""
    
    report_path = os.path.join(results_dir, 'training_report.txt')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("           BÁO CÁO KẾT QUẢ HUẤN LUYỆN MÔ HÌNH MÁY HỌC\n")
        f.write("           IoMT Health Monitoring System\n")
        f.write("=" * 70 + "\n\n")
        
        # Cross-Validation Results
        f.write("1. CROSS-VALIDATION RESULTS (5-Fold Stratified)\n")
        f.write("-" * 50 + "\n")
        f.write(f"   Accuracy:        {cv_results['accuracy']['mean']*100:.2f}% (+/- {cv_results['accuracy']['std']*100*1.96:.2f}%)\n")
        f.write(f"   F1 (weighted):   {cv_results['f1_weighted']['mean']*100:.2f}% (+/- {cv_results['f1_weighted']['std']*100*1.96:.2f}%)\n")
        f.write(f"   F1 (macro):      {cv_results['f1_macro']['mean']*100:.2f}% (+/- {cv_results['f1_macro']['std']*100*1.96:.2f}%)\n")
        f.write(f"   Precision:       {cv_results['precision']['mean']*100:.2f}% (+/- {cv_results['precision']['std']*100*1.96:.2f}%)\n")
        f.write(f"   Recall:          {cv_results['recall']['mean']*100:.2f}% (+/- {cv_results['recall']['std']*100*1.96:.2f}%)\n\n")
        
        # Hyperparameter Tuning Results
        f.write("2. HYPERPARAMETER TUNING RESULTS\n")
        f.write("-" * 50 + "\n")
        f.write(f"   Best CV Score (F1-weighted): {tuning_results['best_score']*100:.2f}%\n\n")
        f.write("   Best Parameters:\n")
        for param, value in tuning_results['best_params'].items():
            f.write(f"      {param}: {value}\n")
        f.write("\n")
        
        # Test Results
        f.write("3. TEST SET EVALUATION\n")
        f.write("-" * 50 + "\n")
        f.write(f"   Test Accuracy:  {test_results['accuracy']:.2f}%\n")
        f.write(f"   Test F1-Score:  {test_results['f1']:.2f}%\n\n")
        f.write("   Classification Report:\n")
        f.write(test_results['classification_report'])
        
        f.write("\n\n" + "=" * 70 + "\n")
        f.write("                     KẾT THÚC BÁO CÁO\n")
        f.write("=" * 70 + "\n")
    
    print(f"\n[REPORT] ✓ Đã lưu báo cáo tại: {report_path}")
    return report_path


def main():
    """Main function."""
    print("=" * 70)
    print("  HUẤN LUYỆN MÔ HÌNH MÁY HỌC")
    print("  + Cross-Validation (5-Fold)")
    print("  + Hyperparameter Tuning (GridSearchCV)")
    print("=" * 70)
    
    # Tạo thư mục
    ensure_dirs()
    
    # 1. Load dữ liệu
    df = load_and_preprocess_data(CSV_PATH)
    
    # 2. Chuẩn bị features và labels
    # Map column names từ CSV (capitalized) sang feature names
    features = ['BPM', 'SpO2', 'Body_Temp', 'GSR_ADC']
    X = df[features].copy()
    y = df['Label'].copy()
    
    print(f"\n[DATA] Features: {features}")
    print(f"[DATA] Tổng mẫu: {len(X)}")
    print(f"[DATA] Class distribution: {dict(y.value_counts())}")
    
    # 3. Baseline Cross-Validation (với default model)
    print("\n" + "=" * 70)
    print("  BASELINE MODEL (Default RandomForest)")
    print("=" * 70)
    
    base_rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    cv_results_baseline = perform_cross_validation(X, y, base_rf, cv_folds=5)
    
    # 4. Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n[DATA] Train size: {len(X_train)} | Test size: {len(X_test)}")
    
    # 5. Hyperparameter Tuning
    best_model, best_params, best_cv_score = perform_hyperparameter_tuning(X_train, y_train, cv_folds=3)
    
    # 6. Đánh giá trên Test Set
    print("\n" + "=" * 70)
    print("  TEST SET EVALUATION (Best Model)")
    print("=" * 70)
    
    y_pred = best_model.predict(X_test)
    test_accuracy = accuracy_score(y_test, y_pred) * 100
    test_f1 = f1_score(y_test, y_pred, average='weighted') * 100
    
    print(f"\n  Test Accuracy: {test_accuracy:.2f}%")
    print(f"  Test F1-Score (weighted): {test_f1:.2f}%")
    print("\n  Classification Report:")
    print(classification_report(y_test, y_pred))
    
    test_results = {
        'accuracy': test_accuracy,
        'f1': test_f1,
        'classification_report': classification_report(y_test, y_pred)
    }
    
    # 7. Retrain trên toàn bộ dữ liệu
    print("\n" + "=" * 70)
    print("  FINAL MODEL TRAINING (Full Dataset)")
    print("=" * 70)
    
    final_model = RandomForestClassifier(**best_params, random_state=42, n_jobs=-1)
    final_model.fit(X, y)
    print(f"[TRAIN] ✓ Đã huấn luyện trên {len(X)} mẫu")
    
    # Lưu model
    joblib.dump(final_model, MODEL_PATH)
    print(f"[MODEL] ✓ Đã lưu model tại: {MODEL_PATH}")
    
    # 8. Visualizations
    classes = sorted(y.unique())
    save_visualizations(y_test, y_pred, classes, final_model, X, RESULTS_DIR)
    
    # 9. Lưu báo cáo
    cv_results = cv_results_baseline
    tuning_results = {'best_params': best_params, 'best_score': best_cv_score}
    save_results_to_file(cv_results, tuning_results, test_results, best_params, RESULTS_DIR)
    
    # 10. Tổng kết
    print("\n" + "=" * 70)
    print("  TỔNG KẾT")
    print("=" * 70)
    print(f"\n  📊 Cross-Validation Accuracy:  {cv_results['accuracy']['mean']*100:.2f}%")
    print(f"  📊 Best CV F1-Score:           {best_cv_score*100:.2f}%")
    print(f"  📊 Test Accuracy:              {test_accuracy:.2f}%")
    print(f"  📊 Test F1-Score:              {test_f1:.2f}%")
    print(f"\n  ⚙️  Best Parameters:")
    for param, value in best_params.items():
        print(f"      {param}: {value}")
    print(f"\n  📁 Kết quả lưu tại: {RESULTS_DIR}")
    print("=" * 70)
    print("  HOÀN TẤT!")
    print("=" * 70)


if __name__ == "__main__":
    main()
