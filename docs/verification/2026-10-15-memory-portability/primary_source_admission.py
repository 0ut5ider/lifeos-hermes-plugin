# ABOUTME: Repeats independent removal source-admission controls with separate primary evidence.
# ABOUTME: Keeps reviewer receipts unchanged while exercising actual grants and service fixtures.
import importlib
from pathlib import Path

review=importlib.import_module('docs.agents.2026-10-15-removal-execution-source-review.source_probes')
review.OUTPUT=Path(__file__).parent/'primary-source-admission'
review.OUTPUT.mkdir(exist_ok=True)
SourceAdmissionReview=review.SourceAdmissionReview
