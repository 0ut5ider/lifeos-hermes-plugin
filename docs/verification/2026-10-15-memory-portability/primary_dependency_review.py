# ABOUTME: Repeats independent contained dependency plan controls with separate primary evidence.
# ABOUTME: Uses captured baseline code and actual filesystem transactions without changing reviewer receipts.
import importlib.util
from pathlib import Path
import shutil

review = Path(__file__).parents[2] / 'agents/2026-10-15-dependency-links-review'
spec = importlib.util.spec_from_file_location('independent_dependency_review', review / 'dependency_probes.py')
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)
controls.OUTPUT = Path(__file__).parent / 'primary-dependency-review'
baseline = controls.OUTPUT / 'baseline/optional/lifeos_release_manager'
baseline.mkdir(parents=True, exist_ok=True)
shutil.copy2(review / 'baseline/optional/lifeos_release_manager/removal_preparation.py', baseline)


class DependencyPlanReview(controls.DependencyPlanReview):
    pass
