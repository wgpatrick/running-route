#!/bin/sh
# Fetch and build Klipper for firmware-in-the-loop runs (mechloop/twin/firmware.py).
# Needs: git, make, gcc-arm-none-eabi, libnewlib-arm-none-eabi, uv.  Nothing is flashed anywhere.
set -e
cd "$(dirname "$0")/.."
COMMIT=29d4ec2d6d840ee839333306003a400da186d41d
mkdir -p third_party
[ -d third_party/klipper ] || git clone -q https://github.com/Klipper3d/klipper third_party/klipper
(cd third_party/klipper && git fetch -q origin "$COMMIT" 2>/dev/null; git checkout -q "$COMMIT" \
  && cp test/configs/stm32g0b1.config .config && make olddefconfig >/dev/null && make -j4 >/dev/null)
[ -d third_party/kenv ] || uv venv -q --python 3.12 third_party/kenv
uv pip install -q --python third_party/kenv/bin/python greenlet cffi Jinja2 markupsafe pyserial setuptools
ls -la third_party/klipper/out/klipper.dict
