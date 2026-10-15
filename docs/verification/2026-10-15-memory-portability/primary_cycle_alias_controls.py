# ABOUTME: Repeats independent cycle alias and cache controls with a selected synthetic Hermes model.
# ABOUTME: Keeps the original assertions and supplies the current activation model prerequisite.
import importlib.util
from pathlib import Path

path=Path(__file__).parents[2]/'agents/2026-10-15-portability-cycle-review/cycle_controls.py'
spec=importlib.util.spec_from_file_location('independent_cycle_controls',path)
controls=importlib.util.module_from_spec(spec);spec.loader.exec_module(controls)


class AliasControls(controls.AliasControls):
    def snapshot(self,text):
        super().snapshot(text+'model: {default: synthetic-model, provider: custom, base_url: "http://127.0.0.1:9/v1", api_key: synthetic-key}\n')
