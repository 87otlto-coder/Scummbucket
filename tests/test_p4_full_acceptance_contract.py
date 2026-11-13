"""Static guard for the mandatory private Room 23 costume acceptance fixture.

These checks are fixture-free. Windows PowerShell syntax is checked separately
in CI; only the private F-drive -Full run can establish actual pixel fidelity.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class P4FullAcceptanceContractTests(unittest.TestCase):
    def test_private_costume_evidence_is_mandatory(self):
        script = (ROOT / "tools/p4_private_acceptance.ps1").read_text(encoding="utf-8")
        test_source = (ROOT / "tests/test_classic_costume.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("SCUMMBUCKET_COSTUME_FIXTURE")', test_source)
        self.assertIn("SCUMMBUCKET_COSTUME_FIXTURE", script)
        self.assertIn(
            "$costumeReport = Join-Path $fixture 'REPORTS\\Room23\\walk-20261110-a.json'",
            script,
        )
        self.assertIn("Test-Path -LiteralPath $costumeReport -PathType Leaf", script)
        self.assertIn(
            "[Environment]::SetEnvironmentVariable('SCUMMBUCKET_COSTUME_FIXTURE', $fixture, 'Process')",
            script,
        )
        # All variables set in the current process must also be restored by finally.
        self.assertIn("'SCUMMBUCKET_COSTUME_FIXTURE')", script)
        self.assertIn(
            "[Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process')",
            script,
        )
        self.assertIn("& python -B -m unittest discover -s tests -v", script)

    def test_private_costume_not_enabled_in_syntax_or_runtime_probe(self):
        script = (ROOT / "tools/p4_private_acceptance.ps1").read_text(encoding="utf-8")
        self.assertLess(script.index("if ($CheckSyntax)"), script.index("$costumeReport ="))
        self.assertLess(script.index("if ($CheckPythonRuntime)"), script.index("$costumeReport ="))
        self.assertIn("if (-not $Full)", script)


if __name__ == "__main__":
    unittest.main()
