import unittest
from unittest.mock import patch

from web.stats import collect_stats, parse_battery_temp, parse_ps, parse_top


TOP_SAMPLE = """
Processes: 525 total, 2 running, 523 sleeping, 3935 threads
Load Avg: 3.06, 2.55, 2.39
CPU usage: 5.43% user, 12.57% sys, 81.98% idle
PhysMem: 23G used (8196M wired, 7290M compressor), 234M unused.
"""

PS_SAMPLE = """
94554     1  42.0  12.5  6291456 /Volumes/Ollama/Ollama.app/Contents/Resources/ollama
94555 94554  18.5   8.0  4194304 /Volumes/Ollama/Ollama.app/Contents/Resources/ollama runner
13194     1   1.2   0.4    81920 python -m web.server
13195 13194   0.8   0.2    40960 python child
99999     1   0.1   0.1     2048 /usr/bin/zsh
"""

BATTERY_SAMPLE = """
+-o AppleSmartBattery  <class AppleSmartBattery, id 0x100>
  {
    "Temperature" = 3068
    "VirtualTemperature" = 3359
  }
"""


class StatsParseTests(unittest.TestCase):
    def test_parse_top_reads_cpu_load_and_unused_ram(self):
        parsed = parse_top(TOP_SAMPLE)
        self.assertEqual(parsed["cpu_percent"], 18.0)
        self.assertEqual(parsed["load_1m"], 3.06)
        self.assertAlmostEqual(parsed["memory_unused_gb"], 0.23, places=2)

    def test_parse_ps_groups_ollama_and_children(self):
        rows = parse_ps(PS_SAMPLE)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["pid"], 94554)
        self.assertAlmostEqual(rows[0]["memory_mb"], 6144.0)

    def test_parse_battery_temp_is_celsius(self):
        self.assertEqual(parse_battery_temp(BATTERY_SAMPLE), 30.7)
        self.assertIsNone(parse_battery_temp(""))

    def test_collect_stats_uses_local_samples(self):
        with (
            patch("web.stats._run", side_effect=_fake_run),
            patch("web.stats._sysctl_int", return_value=24 * 1024**3),
            patch("web.stats.os.getpid", return_value=13194),
            patch("web.stats._cache", {"at": 0.0, "data": None}),
        ):
            data = collect_stats()

        self.assertEqual(data["cpu_percent"], 18.0)
        self.assertEqual(data["memory_total_gb"], 24.0)
        self.assertEqual(data["ollama"]["running"], True)
        self.assertEqual(data["ollama"]["cpu_percent"], 60.5)
        self.assertEqual(data["bchubot"]["running"], True)
        self.assertEqual(data["bchubot"]["cpu_percent"], 2.0)
        self.assertEqual(data["battery_c"], 30.7)


def _fake_run(command, timeout=1.5):
    name = command[0]
    if name == "top":
        return TOP_SAMPLE
    if name == "ps":
        return PS_SAMPLE
    if name == "ioreg":
        return BATTERY_SAMPLE
    return ""


if __name__ == "__main__":
    unittest.main()
