from configs.config import *

print("=" * 60)
print("InfraGuard AI Configuration")
print("=" * 60)

print(f"Project Root : {PROJECT_ROOT}")
print(f"AI Root      : {AI_ROOT}")
print(f"Dataset Root : {DATASET_ROOT}")

print()

print("Classes")

for i, cls in enumerate(CLASS_NAMES):
    print(f"{i} -> {cls}")