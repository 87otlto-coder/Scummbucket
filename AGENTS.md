# Scummbucket AI instructions

Before any development work, read [the standing project instructions](docs/PROJECT_INSTRUCTIONS.md) and [the GitHub Actions incident and Windows-only CI policy](docs/ACTIONS_INCIDENT_2026-11-11.md). Both are mandatory.

The owner develops on Windows. All new or modified GitHub Actions jobs must use Windows hosted runners, not Linux or macOS, unless the owner expressly approves an exception. Do not invent a workflow if the project does not need one. Keep original game inputs and extracted copyrighted assets off GitHub. Preserve reproducibility records, report failures, and follow the newest-three-successful-disposable-build retention rule if artifact-producing CI is introduced.
