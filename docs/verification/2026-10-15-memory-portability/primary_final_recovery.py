# ABOUTME: Repeats independent removal recovery controls with separate primary evidence.
# ABOUTME: Keeps reviewer observations unchanged and uses actual fixture services and children.
import importlib.util
from pathlib import Path

path = Path(__file__).parents[2] / 'agents/2026-10-15-final-removal-review/recovery_probes.py'
spec = importlib.util.spec_from_file_location('independent_final_recovery', path)
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)
controls.OUTPUT = Path(__file__).parent / 'primary-final-recovery'
controls.OUTPUT.mkdir(exist_ok=True)


class FinalRecoveryReview(controls.FinalRecoveryReview):
    pass
