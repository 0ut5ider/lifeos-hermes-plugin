# ABOUTME: Checks that the evening operator changes only the named Pulse schedule.
# ABOUTME: Exercises invalid, duplicate, disabled, and round-trip definitions without services.
import importlib.util
from pathlib import Path
import tomllib
import unittest

spec = importlib.util.spec_from_file_location('evening_operator', Path(__file__).with_name('rescheduled_observation.py'))
operator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operator)


class ScheduleTests(unittest.TestCase):
    before = b'''[settings]\nmarker = "SyntheticEvening"\n[[job]]\nname = "other-job"\nschedule = "*/2 * * * *"\ncommand = "synthetic-other"\n[[job]]\nname = "life-morning-brief"\nschedule = "0 7 * * *"\ntype = "script"\ncommand = "synthetic-qualified-owner-command"\nenabled = true\n'''

    def test_only_selected_schedule_changes_and_round_trip_restores_bytes(self):
        after = operator.replace_schedule(self.before, operator.NORMAL, operator.EVENING)
        expected = tomllib.loads(self.before.decode())
        expected['job'][1]['schedule'] = operator.EVENING
        self.assertEqual(tomllib.loads(after.decode()), expected)
        self.assertEqual(operator.replace_schedule(after, operator.EVENING, operator.NORMAL), self.before)

    def test_missing_duplicate_disabled_or_changed_schedule_refuses(self):
        candidates = [self.before.replace(b'life-morning-brief', b'unknown-job'),
            self.before + b'[[job]]\nname="life-morning-brief"\nschedule="0 7 * * *"\n',
            self.before.replace(b'enabled = true', b'enabled = false'),
            self.before.replace(b'0 7 * * *', b'0 8 * * *'),
            self.before.replace(b'type = "script"', b'type = "claude"')]
        for candidate in candidates:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                operator.replace_schedule(candidate, operator.NORMAL, operator.EVENING)


if __name__ == '__main__': unittest.main()
