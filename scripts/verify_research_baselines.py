import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BaselineSchedulerTests(unittest.TestCase):
    def test_dry_run_preserves_baselines_and_costs(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/run_research_baselines.py'),
             '--snapshot', str(ROOT / 'temp/ws_snapshot_test'), '--tag', 'verification',
             '--dry-run'], capture_output=True, text=True, check=True)
        commands = json.loads(result.stdout)
        self.assertEqual([name for name, _ in commands], ['v81', 'freedom', 'v89'])
        for name, command in commands:
            self.assertEqual(command[command.index('--slippage-bps') + 1], '5')
            self.assertEqual(command[command.index('--max-cached-frames') + 1], '64')
            self.assertTrue(Path(command[2]).is_absolute())
            self.assertEqual(command[command.index('--version') + 1],
                             'v8.9' if name == 'v89' else 'v8.1')

    def test_unsafe_memory_reserve_rejected(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/run_research_baselines.py'),
             '--snapshot', str(ROOT / 'temp/ws_snapshot_test'), '--tag', 'verification',
             '--reserve-gb', '0', '--dry-run'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('memory reserve', result.stderr)


if __name__ == '__main__':
    unittest.main()
