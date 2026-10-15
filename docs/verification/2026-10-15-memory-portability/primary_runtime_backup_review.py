# ABOUTME: Repeats independent portability runtime backup and recovery controls against actual fixtures.
# ABOUTME: Separates primary receipts from the original reviewer evidence.
import importlib
from pathlib import Path

review=importlib.import_module('docs.agents.2026-10-15-portability-runtime-backup-review.backup_probes')
review.OUTPUT=Path(__file__).parent/'primary-runtime-backup-review'
review.OUTPUT.mkdir(exist_ok=True)
PortabilityRuntimeReview=review.PortabilityRuntimeReview
