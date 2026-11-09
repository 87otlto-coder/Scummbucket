#!/usr/bin/env bash
# SCUMM-only Windows build inside an MSYS2 UCRT64 terminal.
# Example:
# bash /f/Dev/SCUMMBUCKET/SOURCE/ScummBucket/tools/build_scummvm_trace_msys2.sh /f/Dev/SCUMMBUCKET/TOOLS/ScummVM-P4-Trace
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "USAGE: bash /f/Dev/SCUMMBUCKET/SOURCE/ScummBucket/tools/build_scummvm_trace_msys2.sh /f/Dev/SCUMMBUCKET/TOOLS/ScummVM-P4-Trace" >&2
  exit 2
fi

if [ "$(printenv MSYSTEM)" != "UCRT64" ]; then
  echo "ERROR: Run this from the MSYS2 UCRT64 shell, not Windows PowerShell or MSYS2 MSYS." >&2
  exit 2
fi

for tool in g++ make git sdl2-config; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "ERROR: '$tool' missing. Install MSYS2 base-devel, GCC and SDL2 first." >&2
    exit 2
  fi
done

root="$1"
if [ ! -f "$root/engines/scumm/scumm.cpp" ]; then
  echo "ERROR: Missing ScummVM source tree: $root" >&2
  exit 2
fi

if ! grep -q 'SCUMMBUCKET_P4_PALETTE_TRACE_V2' "$root/engines/scumm/scumm.cpp"; then
  echo "ERROR: Corrected V2 source hook not installed. Pull latest ScummBucket and run setup_scummvm_trace.ps1 in PowerShell." >&2
  exit 2
fi

# Guard against accidentally compiling the old hook which fails under
# ScummVM's forbidden C stdio APIs.
if grep -q 'SCUMMBUCKET_P4_PALETTE_TRACE_V1' "$root/engines/scumm/scumm.cpp"; then
  echo "ERROR: Legacy V1 hook still present. Run the guarded upgrade in PowerShell." >&2
  exit 2
fi

echo "Building instrumented ScummVM at: $root"
echo "Compiler: $(g++ --version | head -n 1)"
echo "SDL2: $(sdl2-config --version)"
echo "Source revision: $(git -C "$root" rev-parse HEAD)"
cd "$root"

# This source release has a custom ./configure + make build, not CMake.
# Disable unrelated engines for a smaller standalone research build.
./configure \
  --disable-all-engines \
  --enable-engine=scumm \
  --disable-detection-full \
  --disable-cloud \
  --disable-mt32emu \
  --disable-Werror

make -j 4

if [ ! -f scummvm.exe ]; then
  echo "ERROR: Compile finished but scummvm.exe was not found in source root." >&2
  exit 2
fi

echo ""
echo "BUILD COMPLETE: $root/scummvm.exe"
echo "Run this executable from MSYS2 UCRT64 (for its SDL2 / runtime DLL PATH),"
echo "or use the PowerShell capture helper, which adds the default UCRT64 runtime path."
echo "This build was not installed over any existing ScummVM."
