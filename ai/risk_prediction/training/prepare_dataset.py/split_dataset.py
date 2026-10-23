import pandas as pd
from sklearn.model_selection import train_test_split
import os

INPUT_FILE = (
    "C:/Users/DEEPIKA.S/Desktop/mmajor/"
    "InfraGuard-AI/ai/risk_prediction/data/severity_dataset.csv"
)

OUTPUT_DIR = (
    "C:/Users/DEEPIKA.S/Desktop/mmajor/"
    "InfraGuard-AI/ai/risk_prediction/data"
)

df = pd.read_csv(INPUT_FILE)

# First split: 70% train, 30% temporary
train_df, temp_df = train_test_split(
    df,
    test_size=0.30,
    random_state=42,
    stratify=df["severity"]
)

# Second split: 15% validation, 15% test
val_df, test_df = train_test_split(
    temp_df,
    test_size=0.50,
    random_state=42,
    stratify=temp_df["severity"]
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

train_df.to_csv(
    os.path.join(OUTPUT_DIR, "train.csv"),
    index=False
)

val_df.to_csv(
    os.path.join(OUTPUT_DIR, "validation.csv"),
    index=False
)

test_df.to_csv(
    os.path.join(OUTPUT_DIR, "test.csv"),
    index=False
)

print("Dataset split completed.")

print(f"Training:   {len(train_df)}")
print(f"Validation: {len(val_df)}")
print(f"Test:       {len(test_df)}")

print("\nTraining distribution:")
print(train_df["severity"].value_counts())

print("\nValidation distribution:")
print(val_df["severity"].value_counts())

print("\nTest distribution:")
print(test_df["severity"].value_counts())