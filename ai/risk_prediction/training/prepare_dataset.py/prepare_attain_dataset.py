import os
import xml.etree.ElementTree as ET
import pandas as pd


# ============================================================
# PATHS
# ============================================================

LABEL_DIR = r"D:\Attain\Attain\Attain\Attain_SMP_WS_V2.0\Labels"

OUTPUT_DIR = r"C:\Users\DEEPIKA.S\Desktop\mmajor\InfraGuard-AI\ai\risk_prediction\data"

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "severity_dataset.csv")


# ============================================================
# DAMAGE TYPES
# ============================================================

DAMAGE_TYPES = {
    "Alligator crack": "alligator_crack",
    "Block crack": "block_crack",
    "Faded marking": "faded_marking",
    "Lane shoulder drop-off": "lane_shoulder_dropoff",
    "Linear crack": "linear_crack",
    "Patch and utility cut": "patch_utility_cut",
    "Pothole": "pothole",
    "Raveling": "raveling",
    "Weathering": "weathering",
}


# ============================================================
# PROCESS XML FILES
# ============================================================

rows = []

xml_files = [
    f for f in os.listdir(LABEL_DIR)
    if f.lower().endswith(".xml")
]

print(f"Found {len(xml_files)} XML files.")


for xml_file in xml_files:

    xml_path = os.path.join(LABEL_DIR, xml_file)

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        filename = root.findtext("filename", default="")

        width = int(root.findtext("size/width", default="0"))
        height = int(root.findtext("size/height", default="0"))

        image_area = width * height

        counts = {
            value: 0
            for value in DAMAGE_TYPES.values()
        }

        total_damage_area = 0
        high_found = False
        total_objects = 0

        objects = root.findall("object")

        for obj in objects:

            name = obj.findtext("name", default="").strip()

            # ------------------------------------------------
            # Determine severity
            # ------------------------------------------------

            if "High" in name:
                high_found = True

            # ------------------------------------------------
            # Determine damage type
            # ------------------------------------------------

            damage_type = None

            for original_name, feature_name in DAMAGE_TYPES.items():

                if name.startswith(original_name):
                    damage_type = feature_name
                    break

            if damage_type is None:
                continue

            counts[damage_type] += 1
            total_objects += 1

            # ------------------------------------------------
            # Bounding box area
            # ------------------------------------------------

            bbox = obj.find("bndbox")

            if bbox is not None:

                xmin = float(bbox.findtext("xmin", default="0"))
                xmax = float(bbox.findtext("xmax", default="0"))
                ymin = float(bbox.findtext("ymin", default="0"))
                ymax = float(bbox.findtext("ymax", default="0"))

                box_width = max(0, xmax - xmin)
                box_height = max(0, ymax - ymin)

                total_damage_area += box_width * box_height

        # ----------------------------------------------------
        # Damage area ratio
        # ----------------------------------------------------

        if image_area > 0:
            damage_area_ratio = total_damage_area / image_area
        else:
            damage_area_ratio = 0

        # ----------------------------------------------------
        # Image-level severity
        #
        # If at least one object is High,
        # classify the complete image as High.
        # Otherwise Low.
        # ----------------------------------------------------

        severity = "High" if high_found else "Low"

        row = {
            "image_name": filename,

            **counts,

            "total_damage_count": total_objects,

            "damage_area_ratio": damage_area_ratio,

            "severity": severity,
        }

        rows.append(row)

    except Exception as e:

        print(f"Error processing {xml_file}: {e}")


# ============================================================
# CREATE DATAFRAME
# ============================================================

df = pd.DataFrame(rows)


# ============================================================
# SAVE DATASET
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

df.to_csv(OUTPUT_FILE, index=False)


# ============================================================
# SUMMARY
# ============================================================

print("\nDataset created successfully.")

print(f"Images processed: {len(df)}")

print("\nSeverity distribution:")
print(df["severity"].value_counts())

print("\nDataset columns:")
print(df.columns.tolist())

print(f"\nSaved to:")
print(OUTPUT_FILE)