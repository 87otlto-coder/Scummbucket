"""Repository-level tests for the agreed Windows workspace conventions.

These are static safety checks; they do not replace execution of the PowerShell
migration on the user's Windows machine or prove a copied executable launches.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


class WorkspaceLayoutTest(unittest.TestCase):
    def test_setup_defaults_to_external_tools(self):
        data = read("tools/setup_scummvm_trace.ps1")
        self.assertIn(r"F:\Dev\SCUMMBUCKET\TOOLS\ScummVM-P4-Trace", data)
        self.assertNotIn(r"Join-Path $HOME 'ScummVM-P4-Trace'", data)

    def test_capture_uses_fixture_not_repo_reports(self):
        data = read("tools/run_scummvm_palette_capture.ps1")
        self.assertIn(r"F:\Dev\SCUMMBUCKET", data)
        self.assertIn(r"FIXTURE\GAMES\MonkeyIsland2_DOS_VGA", data)
        self.assertIn(r"FIXTURE\CAPTURES\Room23", data)
        self.assertIn(r"FIXTURE\REPORTS\Room23", data)
        self.assertNotIn("$exportDir = Join-Path $repoRoot 'exports'", data)
        self.assertNotIn("$reportDir = Join-Path $repoRoot 'reports'", data)
        self.assertIn("CAPTURE_MODE_NOT_OBSERVED", data)
        self.assertIn("SCUMMBUCKET_P4_PALETTE_TRACE_V2", data)

    def test_msys2_build_example_uses_f_drive(self):
        data = read("tools/build_scummvm_trace_msys2.sh")
        self.assertIn("/f/Dev/SCUMMBUCKET/SOURCE/ScummBucket/tools/", data)
        self.assertIn("/f/Dev/SCUMMBUCKET/TOOLS/ScummVM-P4-Trace", data)
        self.assertNotIn("/c/Users/87otl/ScummBucket", data)

    def test_migration_is_preview_first_and_copy_only(self):
        data = read("tools/migrate_workspace.ps1")
        self.assertIn("[switch]$Apply", data)
        self.assertIn("PREVIEW_COMPLETE", data)
        self.assertIn("Copy-FreshTree", data)
        self.assertIn("Verify-Identical", data)
        self.assertIn("Get-FileHash", data)
        self.assertIn("originals_deleted = $false", data)
        self.assertNotIn("Remove-Item", data)
        self.assertNotIn("Move-Item", data)
        for folder in ("SOURCE", "TOOLS", "FIXTURE"):
            self.assertIn(folder, data)

    def test_project_instructions_use_three_folder_standard(self):
        data = read("docs/PROJECT_INSTRUCTIONS.md")
        self.assertIn(r"F:\Dev\SCUMMBUCKET", data)
        self.assertIn(r"SOURCE\ScummBucket", data)
        self.assertIn(r"TOOLS\ScummVM-P4-Trace", data)
        self.assertIn(r"FIXTURE\GAMES", data)
        self.assertNotIn(r"C:\Users\87otl\ScummBucket", data)


if __name__ == "__main__":
    unittest.main()
