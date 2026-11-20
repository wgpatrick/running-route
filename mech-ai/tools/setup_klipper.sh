#!/bin/sh
# Fetch and build Klipper for firmware-in-the-loop runs (mechloop/twin/firmware.py).
# Needs: git, make, gcc-arm-none-eabi, libnewlib-arm-none-eabi, uv.  Nothing is flashed anywhere.
set -e
cd "$(dirname "$0")/.."
COMMIT=29d4ec2d6d840ee839333306003a400da186d41d
mkdir -p third_party
[ -d third_party/klipper ] || git clone -q https://github.com/Klipper3d/klipper third_party/klipper
(cd third_party/klipper && git fetch -q origin "$COMMIT" 2>/dev/null; git checkout -q "$COMMIT" \
  && cp test/configs/stm32g0b1.config .config && make olddefconfig >/dev/null && make -j4 >/dev/null \
  && cp test/configs/stm32f446.config .config.stm32f446 \
  && make OUT=out_stm32f446/ KCONFIG_CONFIG=.config.stm32f446 olddefconfig >/dev/null \
  && make OUT=out_stm32f446/ KCONFIG_CONFIG=.config.stm32f446 -j4 >/dev/null \
  && cp test/configs/rp2040.config .config.rp2040 \
  && make OUT=out_rp2040/ KCONFIG_CONFIG=.config.rp2040 olddefconfig >/dev/null \
  && make OUT=out_rp2040/ KCONFIG_CONFIG=.config.rp2040 -j4 >/dev/null \
  && cp test/configs/linuxprocess.config .config.linux \
  && make OUT=out_linux/ KCONFIG_CONFIG=.config.linux olddefconfig >/dev/null \
  && make OUT=out_linux/ KCONFIG_CONFIG=.config.linux -j4 >/dev/null)
# out_rp2040/ (BTT Eddy Duo, BTT ADXL345 V2: secondary MCUs over USB) and out_linux/ (the Pi's host MCU) are passed to klippy as
# '-d <name>=...' for '[mcu <name>]' sections marked '# klipper_mcu: rp2040' / 'linux' (mechloop/twin/firmware.py)
# out/ (STM32G0B1: SKR Mini E3 V3, MANTA M5P) is the default; out_stm32f446/ is used for a printer.cfg that says
# '# klipper_mcu: stm32f446' (BTT Octopus V1.1, mechloop/twin/firmware.py mcu_dictionary)
[ -d third_party/kenv ] || uv venv -q --python 3.12 third_party/kenv
uv pip install -q --python third_party/kenv/bin/python greenlet cffi Jinja2 markupsafe pyserial setuptools
ls -la third_party/klipper/out/klipper.dict third_party/klipper/out_stm32f446/klipper.dict
