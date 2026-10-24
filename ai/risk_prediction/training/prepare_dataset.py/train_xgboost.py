import os
import pandas as pd
import joblib

from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


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

MODEL_DIR = os.path.join(
    BASE_DIR,
    "ai",
    "risk_prediction",
    "models"
)

os.makedirs(MODEL_DIR, exist_ok=True)


# --------------------------------------------------
# Load datasets
# --------------------------------------------------

train_df = pd.read_csv(
    os.path.join(DATA_DIR, "train.csv")
)

val_df = pd.read_csv(
    os.path.join(DATA_DIR, "validation.csv")
)

test_df = pd.read_csv(
    os.path.join(DATA_DIR, "test.csv")
)


# --------------------------------------------------
# Feature columns
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


# --------------------------------------------------
# Prepare X and y
# --------------------------------------------------

X_train = train_df[FEATURE_COLUMNS]
X_val = val_df[FEATURE_COLUMNS]
X_test = test_df[FEATURE_COLUMNS]

# Low = 0
# High = 1

y_train = train_df["severity"].map({
    "Low": 0,
    "High": 1
})

y_val = val_df["severity"].map({
    "Low": 0,
    "High": 1
})

y_test = test_df["severity"].map({
    "Low": 0,
    "High": 1
})


# --------------------------------------------------
# Create XGBoost model
# --------------------------------------------------

model = XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="binary:logistic",
    eval_metric="logloss",
    random_state=42
)


# --------------------------------------------------
# Train
# --------------------------------------------------

print("Training XGBoost severity model...")

model.fit(
    X_train,
    y_train,
    eval_set=[(X_val, y_val)],
    verbose=False
)


# --------------------------------------------------
# Validation evaluation
# --------------------------------------------------

val_predictions = model.predict(X_val)

val_accuracy = accuracy_score(y_val, val_predictions)
val_precision = precision_score(y_val, val_predictions)
val_recall = recall_score(y_val, val_predictions)
val_f1 = f1_score(y_val, val_predictions)

print("\nValidation Results")
print("------------------")
print(f"Accuracy : {val_accuracy:.4f}")
print(f"Precision: {val_precision:.4f}")
print(f"Recall   : {val_recall:.4f}")
print(f"F1 Score : {val_f1:.4f}")


# --------------------------------------------------
# Final test evaluation
# --------------------------------------------------

test_predictions = model.predict(X_test)

test_accuracy = accuracy_score(y_test, test_predictions)
test_precision = precision_score(y_test, test_predictions)
test_recall = recall_score(y_test, test_predictions)
test_f1 = f1_score(y_test, test_predictions)

print("\nTest Results")
print("------------")
print(f"Accuracy : {test_accuracy:.4f}")
print(f"Precision: {test_precision:.4f}")
print(f"Recall   : {test_recall:.4f}")
print(f"F1 Score : {test_f1:.4f}")


# --------------------------------------------------
# Save model
# --------------------------------------------------

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "severity_xgboost.pkl"
)

joblib.dump(model, MODEL_PATH)

print("\nModel saved successfully:")
print(MODEL_PATH)