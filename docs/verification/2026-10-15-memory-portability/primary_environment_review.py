# ABOUTME: Repeats independent environment normalization controls through the actual stock runtime.
# ABOUTME: Saves primary evidence separately from the immutable reviewer output.
import importlib
from pathlib import Path

review=importlib.import_module('docs.agents.2026-10-15-removal-environment-review.environment_probes')
review.OUTPUT=Path(__file__).parent/'primary-environment-review'
review.OUTPUT.mkdir(exist_ok=True)
EnvironmentReview=review.EnvironmentReview
