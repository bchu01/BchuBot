import unittest

from tools.registry import TOOL_REGISTRY, describe_capabilities


class CapabilitiesTests(unittest.TestCase):
    def test_capability_summary_covers_every_tool(self):
        summary = describe_capabilities()
        for name in TOOL_REGISTRY:
            self.assertIn(name, summary)

    def test_weather_source_is_open_meteo(self):
        summary = describe_capabilities()
        self.assertIn("Open-Meteo", summary)
        self.assertIn("open-meteo.com", summary)


if __name__ == "__main__":
    unittest.main()
