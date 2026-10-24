import os
import pandas as pd
import joblib
import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    ConfusionMatrixDisplay,
    classification_report,
)


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = r"C:\Users\DEEPIKA.S\Desktop\mmajor\InfraGuard-AI"

DATA_DIR = os.path.join(
    BASE_DIR,
    "ai",
    "risk_prediction",
    "data"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "ai",
    "risk_prediction",
    "models",
    "severity_xgboost.pkl"
)

EVALUATION_DIR = os.path.join(
    BASE_DIR,
    "ai",
    "risk_prediction",
    "evaluation"
)

os.makedirs(EVALUATION_DIR, exist_ok=True)


# --------------------------------------------------
# Load test dataset and model
# --------------------------------------------------

test_df = pd.read_csv(
    os.path.join(DATA_DIR, "test.csv")
)

model = joblib.load(MODEL_PATH)


# --------------------------------------------------
# Features
# --------------------------------------------------

FEATURE_COLUMNS = [
    "alligator_crack",
    "block_crack",
    "faded_marking",
    "lane_shoulder_dropoff",
    "linear_crack",
    "patch_utility_cut",
    "pothole",
    "raveling",
    "weathering",
    "total_damage_count",
    "damage_area_ratio",
]


X_test = test_df[FEATURE_COLUMNS]

y_test = test_df["severity"].map({
    "Low": 0,
    "High": 1
})


# --------------------------------------------------
# Predictions
# --------------------------------------------------

predictions = model.predict(X_test)

probabilities = model.predict_proba(X_test)[:, 1]


# --------------------------------------------------
# Metrics
# --------------------------------------------------

accuracy = accuracy_score(y_test, predictions)
precision = precision_score(y_test, predictions)
recall = recall_score(y_test, predictions)
f1 = f1_score(y_test, predictions)
roc_auc = roc_auc_score(y_test, probabilities)


print("\nFinal Test Evaluation")
print("=====================")
print(f"Accuracy : {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall   : {recall:.4f}")
print(f"F1 Score : {f1:.4f}")
print(f"ROC-AUC  : {roc_auc:.4f}")


# --------------------------------------------------
# Classification report
# --------------------------------------------------

report = classification_report(
    y_test,
    predictions,
    target_names=["Low", "High"]
)

print("\nClassification Report")
print("=====================")
print(report)


# Save classification report
report_path = os.path.join(
    EVALUATION_DIR,
    "classification_report.txt"
)

with open(report_path, "w") as f:
    f.write("InfraGuard-AI XGBoost Severity Model\n")
    f.write("Final Test Evaluation\n\n")
    f.write(f"Accuracy : {accuracy:.4f}\n")
    f.write(f"Precision: {precision:.4f}\n")
    f.write(f"Recall   : {recall:.4f}\n")
    f.write(f"F1 Score : {f1:.4f}\n")
    f.write(f"ROC-AUC  : {roc_auc:.4f}\n\n")
    f.write("Classification Report\n")
    f.write("=====================\n")
    f.write(report)


# --------------------------------------------------
# Confusion Matrix
# --------------------------------------------------

cm = confusion_matrix(y_test, predictions)

disp = ConfusionMatrixDisplay(
    confusion_matrix=cm,
    display_labels=["Low", "High"]
)

disp.plot()

plt.title("InfraGuard-AI Severity Model - Confusion Matrix")
plt.tight_layout()

cm_path = os.path.join(
    EVALUATION_DIR,
    "confusion_matrix.png"
)

plt.savefig(cm_path, dpi=300)
plt.close()


# --------------------------------------------------
# Feature Importance
# --------------------------------------------------

importance = model.feature_importances_

importance_df = pd.DataFrame({
    "feature": FEATURE_COLUMNS,
    "importance": importance
})

importance_df = importance_df.sort_values(
    "importance",
    ascending=True
)

plt.figure(figsize=(10, 6))

plt.barh(
    importance_df["feature"],
    importance_df["importance"]
)

plt.xlabel("Importance")
plt.ylabel("Feature")
plt.title("XGBoost Feature Importance")

plt.tight_layout()

importance_path = os.path.join(
    EVALUATION_DIR,
    "feature_importance.png"
)

plt.savefig(
    importance_path,
    dpi=300
)

plt.close()


print("\nEvaluation files saved:")
print(report_path)
print(cm_path)
print(importance_path)