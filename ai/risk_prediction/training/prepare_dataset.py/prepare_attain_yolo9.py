import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


# ============================================================
# Paths
# ============================================================

ATTain_ROOT = Path(
    r"D:\Attain\Attain\Attain\Attain_SMP_WS_V2.0"
)

LABEL_DIR = ATTain_ROOT / "Labels"

IMAGE_CANDIDATES = [
    ATTain_ROOT / "Images",
    ATTain_ROOT / "images",
    ATTain_ROOT / "Image",
    ATTain_ROOT / "image",
]

OUTPUT_ROOT = (
    Path(r"C:\Users\DEEPIKA.S\Desktop\mmajor\InfraGuard-AI")
    / "ai"
    / "computer_vision"
    / "data"
    / "attain_9class"
)


# ============================================================
# Nine YOLO classes
# ============================================================

CLASS_NAMES = [
    "alligator_crack",
    "block_crack",
    "linear_crack",
    "pothole",
    "raveling",
    "weathering",
    "faded_marking",
    "patch_utility_cut",
    "lane_shoulder_dropoff",
]


CLASS_MAP = {
    "Alligator crack": 0,
    "Block crack": 1,
    "Linear crack": 2,
    "Pothole": 3,
    "Raveling": 4,
    "Weathering": 5,
    "Faded marking": 6,
    "Patch and utility cut": 7,
    "Lane shoulder drop-off": 8,
}


# ============================================================
# Find image directory
# ============================================================

IMAGE_DIR = None

for candidate in IMAGE_CANDIDATES:
    if candidate.exists():
        IMAGE_DIR = candidate
        break

if IMAGE_DIR is None:
    print("ERROR: Could not find the Attain image folder.")
    print("Expected one of:")

    for candidate in IMAGE_CANDIDATES:
        print(candidate)

    raise SystemExit(1)


print("Label directory:")
print(LABEL_DIR)

print("\nImage directory:")
print(IMAGE_DIR)

print("\nOutput directory:")
print(OUTPUT_ROOT)


# ============================================================
# Create YOLO folder structure
# ============================================================

for split in ["train", "val", "test"]:

    (OUTPUT_ROOT / "images" / split).mkdir(
        parents=True,
        exist_ok=True
    )

    (OUTPUT_ROOT / "labels" / split).mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# Collect XML files
# ============================================================

xml_files = sorted(
    LABEL_DIR.glob("*.xml")
)

print(
    f"\nFound {len(xml_files)} XML annotation files."
)


# ============================================================
# Convert XML → YOLO
# ============================================================

converted = 0
skipped = 0

object_counts = {
    class_name: 0
    for class_name in CLASS_NAMES
}


for xml_path in xml_files:

    try:

        tree = ET.parse(xml_path)
        root = tree.getroot()

        filename = root.findtext(
            "filename",
            default=""
        ).strip()

        width = int(
            root.findtext(
                "size/width",
                default="0"
            )
        )

        height = int(
            root.findtext(
                "size/height",
                default="0"
            )
        )

        if width <= 0 or height <= 0:
            skipped += 1
            continue


        # ----------------------------------------------------
        # Locate image
        # ----------------------------------------------------

        image_path = IMAGE_DIR / filename

        if not image_path.exists():

            matches = list(
                IMAGE_DIR.glob(
                    Path(filename).stem + ".*"
                )
            )

            if matches:
                image_path = matches[0]

            else:
                print(
                    f"WARNING: Image not found: {filename}"
                )

                skipped += 1
                continue


        # ----------------------------------------------------
        # Collect YOLO objects
        # ----------------------------------------------------

        yolo_lines = []

        for obj in root.findall("object"):

            # IMPORTANT:
            # Normalize whitespace because some XML labels
            # contain line breaks inside the class name.
            #
            # Example:
            #
            # Patch and
            # utility cut- Low
            #
            # becomes:
            #
            # Patch and utility cut- Low

            raw_name = obj.findtext(
                "name",
                default=""
            )

            name = " ".join(
                raw_name.split()
            ).strip()


            # ------------------------------------------------
            # Remove severity suffix
            # ------------------------------------------------

            # Examples:
            #
            # Pothole - High
            # Pothole - Low
            #
            # Patch and utility cut- Low
            #
            # all become:
            #
            # Pothole
            # Patch and utility cut

            base_name = name.rsplit(
                "-",
                1
            )[0].strip()


            # ------------------------------------------------
            # Check supported class
            # ------------------------------------------------

            if base_name not in CLASS_MAP:
                continue

            class_id = CLASS_MAP[base_name]


            # ------------------------------------------------
            # Bounding box
            # ------------------------------------------------

            bbox = obj.find("bndbox")

            if bbox is None:
                continue


            xmin = float(
                bbox.findtext(
                    "xmin",
                    default="0"
                )
            )

            ymin = float(
                bbox.findtext(
                    "ymin",
                    default="0"
                )
            )

            xmax = float(
                bbox.findtext(
                    "xmax",
                    default="0"
                )
            )

            ymax = float(
                bbox.findtext(
                    "ymax",
                    default="0"
                )
            )


            # ------------------------------------------------
            # Clamp coordinates
            # ------------------------------------------------

            xmin = max(
                0,
                min(xmin, width)
            )

            xmax = max(
                0,
                min(xmax, width)
            )

            ymin = max(
                0,
                min(ymin, height)
            )

            ymax = max(
                0,
                min(ymax, height)
            )


            # ------------------------------------------------
            # Validate bounding box
            # ------------------------------------------------

            if xmax <= xmin or ymax <= ymin:
                continue


            # ------------------------------------------------
            # Convert to YOLO format
            # ------------------------------------------------

            x_center = (
                (xmin + xmax) / 2
            ) / width

            y_center = (
                (ymin + ymax) / 2
            ) / height

            box_width = (
                xmax - xmin
            ) / width

            box_height = (
                ymax - ymin
            ) / height


            yolo_lines.append(
                f"{class_id} "
                f"{x_center:.6f} "
                f"{y_center:.6f} "
                f"{box_width:.6f} "
                f"{box_height:.6f}"
            )


            object_counts[
                CLASS_NAMES[class_id]
            ] += 1


        # ----------------------------------------------------
        # Skip images with no supported objects
        # ----------------------------------------------------

        if not yolo_lines:
            skipped += 1
            continue


        # ----------------------------------------------------
        # Deterministic split
        # ----------------------------------------------------

        index = converted % 10

        if index < 7:
            split = "train"

        elif index < 8:
            split = "val"

        else:
            split = "test"


        # ----------------------------------------------------
        # Copy image
        # ----------------------------------------------------

        destination_image = (
            OUTPUT_ROOT
            / "images"
            / split
            / image_path.name
        )

        shutil.copy2(
            image_path,
            destination_image
        )


        # ----------------------------------------------------
        # Save YOLO label
        # ----------------------------------------------------

        label_path = (
            OUTPUT_ROOT
            / "labels"
            / split
            / f"{image_path.stem}.txt"
        )

        label_path.write_text(
            "\n".join(yolo_lines) + "\n",
            encoding="utf-8"
        )


        converted += 1


    except Exception as exc:

        print(
            f"ERROR processing {xml_path.name}: {exc}"
        )

        skipped += 1


# ============================================================
# Create data.yaml
# ============================================================

yaml_path = OUTPUT_ROOT / "data.yaml"

yaml_content = f"""path: {OUTPUT_ROOT.as_posix()}
train: images/train
val: images/val
test: images/test

names:
"""

for index, class_name in enumerate(CLASS_NAMES):

    yaml_content += (
        f"  {index}: {class_name}\n"
    )


yaml_path.write_text(
    yaml_content,
    encoding="utf-8"
)


# ============================================================
# Summary
# ============================================================

print("\n========================================")
print("9-CLASS YOLO DATASET PREPARATION DONE")
print("========================================")

print(
    f"Converted images: {converted}"
)

print(
    f"Skipped images:   {skipped}"
)

print("\nObject counts:")

for class_name, count in object_counts.items():

    print(
        f"{class_name:25s}: {count}"
    )

print("\nDataset YAML:")
print(yaml_path)

print("\nOutput directory:")
print(OUTPUT_ROOT)