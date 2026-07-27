"""
InfraGuard AI
Computer Vision — Training Package

Exposes the public entry-points for the training pipeline so
callers can import directly from the package:

    from training.callbacks import register_callbacks
    from training.evaluate import evaluate
    from training.export import export_all

Pipeline order (for reference):

    1. train.py
         └── register_callbacks(model, cfg)
               ├── on_train_start
               ├── on_fit_epoch_end  (per epoch)
               ├── on_val_end        (per epoch)
               └── on_train_end

    2. evaluate.py
         └── evaluate(weights_path, config_path, class_names)
               ├── load_eval_config
               ├── validate_model_exists
               ├── load_model
               ├── run_val              (TEST split only)
               ├── extract_overall_metrics
               ├── extract_per_class_metrics
               ├── copy_ultralytics_plots
               ├── save_metrics_csv
               ├── save_summary_json
               └── print_eval_report

    3. export.py
         └── export_all(weights_path, config_path)
               ├── load_export_config
               ├── resolve_export_targets
               ├── validate_model_exists  (hard stop)
               ├── load_model_for_export  (loaded once, reused)
               ├── _dispatch_export       (per enabled format)
               │     ├── _export_pytorch   → exports/<exp>/<exp>.pt
               │     ├── _export_onnx      → exports/<exp>/<exp>.onnx
               │     ├── _export_tensorrt  → exports/<exp>/<exp>.engine
               │     └── _export_tflite    → exports/<exp>/<exp>.tflite
               ├── save_export_manifest   → exports/<exp>/export_manifest.json
               └── print_export_summary
"""

from training.callbacks import register_callbacks
from training.evaluate import evaluate
from training.export import export_all

__all__ = [
    "register_callbacks",
    "evaluate",
    "export_all",
]
