"""Input contracts that prevent silent invalid comparisons."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("local", ROOT / "scripts" / "delineo_local.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)


class InputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        path = Path(cls.tmp.name) / "data"
        local.fixture(path)
        cls.pap = local.read_json(path / "pap.json")
        cls.patterns = local.read_json(path / "patterns.json")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.config = local.read_json(ROOT / "configs" / "teaching.json")

    def test_fixture_valid(self):
        local.validate(self.config, self.pap, self.patterns)

    def test_percent_not_fraction_rejected(self):
        self.config["interventions"][0]["mask"] = 50
        with self.assertRaisesRegex(ValueError, "fraction"):
            local.validate(self.config, self.pap, self.patterns)

    def test_duplicate_location_rejected(self):
        bad = copy.deepcopy(self.patterns)
        bad["60"]["places"]["1001"] = ["0"]
        with self.assertRaisesRegex(ValueError, "multiply located"):
            local.validate(self.config, self.pap, bad)

    def test_missing_frame_rejected(self):
        bad = dict(self.patterns)
        del bad["60"]
        with self.assertRaisesRegex(ValueError, "one frame per hour"):
            local.validate(self.config, self.pap, bad)

    def test_unknown_seed_person_rejected(self):
        self.config["initial_infected_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "Initial IDs"):
            local.validate(self.config, self.pap, self.patterns)

    def test_no_silent_dmp_fallback(self):
        self.config["dmp_mode"] = "auto"
        with self.assertRaisesRegex(ValueError, "auto is forbidden"):
            local.validate(self.config, self.pap, self.patterns)

    def test_nonfinite_rate_rejected(self):
        self.config["ventilation_coeff"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            local.validate(self.config, self.pap, self.patterns)


if __name__ == "__main__":
    unittest.main()
