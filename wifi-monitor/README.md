# Malachite passive Wi-Fi monitor

This repository contains an experimental passive 802.11 capture patch for the
MediaTek MT6878 gen4m driver and an optional KernelSU control helper.

- [Build and integration](patches/BUILD.md) documents the pinned source, the
  target module and the compatibility checks for a dedicated test ROM.
- [Engineering audit](AUDIT-2026-11-13.md) records defects, validation results
  and the remaining hardware tests.
- KernelSU 1.3 displays status from its Action button. Explicit root commands
  control a test driver already loaded by the ROM. The module performs no
  boot-time driver swap and ships no kernel payload.
- The transmit experiments and the November 10–12 notes are historical.
  The supported build selects only patch 0001 and drops monitor-interface TX.

Use the exact Android Image and module set qualified for the test handset.
MT6878 alone does not establish model, firmware or ABI compatibility.
