# Build and integrate the passive monitor driver

## Source and build

Use the pinned manifest for the malachite kernel source build. The audited
kernel revision is `fc1616578c449fc0bf4a6a061046e2992347f3c6` (6.1.167),
and the MediaTek modules revision is
`ce0e09550e0952ede49a10b602aa0198f52d625f`. Confirm both revisions
before applying the patch. Work in a clean, separate source checkout.

```sh
vendor=vendor/mediatek/kernel_modules
patch=/absolute/path/to/wifi-monitor-injection/patches/0001-gen4m-passive-monitor.patch
git -C "$vendor" apply --check --ignore-whitespace --whitespace=error "$patch"
git -C "$vendor" apply --ignore-whitespace --whitespace=error "$patch"
git -C "$vendor" -c core.whitespace=cr-at-eol diff --check

export KERNEL_VERSION=kernel-6.1 DEFCONFIG_OVERLAYS=malachite.config
export SOURCE_DATE_EPOCH="$(git -C kernel-6.1 show -s --format=%ct HEAD)"
target=//vendor/mediatek/kernel_modules/connectivity/wlan/core/gen4m/build/connac2x/6878:wlan_drv_gen4m_6878.mgk_64_k61.6.1.user
tools/bazel --batch build "$target" --//build/bazel_mgk_rules:kernel_version=6.1 \
  --repo_env=KERNEL_VERSION="$KERNEL_VERSION" \
  --repo_env=DEFCONFIG_OVERLAYS="$DEFCONFIG_OVERLAYS" \
  --repo_env=SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" --jobs=6
```

The MT6878 Kbuild enables radiotap and disables the vendor PDMA scatter
reassembly for this build. The kernel config fragment is unnecessary for
this target. Patch 0001 is the complete supported patch set.

## Integration gate

Check every imported symbol and CRC against the actual Image and load-list
modules. Check reverse dependencies for every proposed replacement, plus
module name, architecture, vermagic flags, signing and SELinux. Run the
same check on the original set as a control. The locally shipped 6.1.166
Image has 6.1.115 Wi-Fi modules. A matched 6.1.167 source build can resolve
the inter-module CRC differences while still leaving Image compatibility
and runtime behavior to verify. An ELF header or successful link cannot
establish compatibility. [Android kernel ABI monitoring](https://source.android.com/docs/core/architecture/kernel/abi-monitor)

Keep the original Image, module set and load order available for recovery.
Any approved integration belongs in a dedicated test ROM built through
the normal module-loading path. The KernelSU helper has no driver payload
and performs no boot-time work. Use the [audit](../AUDIT-2026-11-13.md)
for the staged hardware test and rollback criteria.

## Optional KernelSU control

Install the helper from the files under
`ksu-module/malachite-wifi-monitor/` after the test ROM is qualified.
If replacing version 1.2.x, confirm that the passive helper update has
taken effect and that the old boot hook is absent before testing.
[KernelSU module guide](https://kernelsu.org/guide/module.html)

It uses an Android-native `iw`, Android `settings`, `ip` and `flock`.
The resident module marker at
`/sys/module/wlan_drv_gen4m_6878/version` must read
`malachite-passive-1`. Use the artifact digest and the test ROM build
record to verify provenance. The marker is a build-family check.

The Action button is read-only. For a passive session, turn Android Wi-Fi
and hotspot off and verify the test ROM still exposes a down, managed
`wlan0` without active concurrent interfaces. With root privileges use
`action.sh arm 6` or `action.sh arm 36`. Run `action.sh disarm` before
changing channels or re-enabling Android Wi-Fi. The helper leaves
`wlan0` managed and down when disarm succeeds. A setup error triggers
an attempt to undo the changes, with recovery left available on failure.
The capture itself is the channel check because the firmware command
has no response and the driver's channel readback is unimplemented.
