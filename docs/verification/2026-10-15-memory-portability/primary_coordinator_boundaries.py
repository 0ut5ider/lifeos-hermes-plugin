# ABOUTME: Repeats the independent detached coordinator controls without replacing the reviewer's receipts.
# ABOUTME: Saves primary observations in a separate safe verification directory.
import importlib.util
from pathlib import Path

path=Path(__file__).parents[2]/'agents/2026-10-15-removal-coordinator-review/coordinator_probes.py'
spec=importlib.util.spec_from_file_location('independent_coordinator_controls',path)
controls=importlib.util.module_from_spec(spec);spec.loader.exec_module(controls)
controls.OUTPUT=Path(__file__).parent/'primary-coordinator-boundaries'
controls.OUTPUT.mkdir(exist_ok=True)


class CoordinatorBoundaryReview(controls.CoordinatorBoundaryReview):
    pass
