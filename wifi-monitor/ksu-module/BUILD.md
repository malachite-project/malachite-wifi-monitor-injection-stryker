# Combined module — malachite: Stryker + Wi-Fi monitor

Flashable KernelSU/Magisk zip bundling the gen4m driver + the Stryker APK.

## Assemble the zip
1. Build the driver .ko (cfg80211.ko + wlan_drv_gen4m_6878.ko, vermagic 6.1.167)
   from ../patches/ and drop them in modules/.
2. Build the app: `:app:assembleRelease` and copy the APK here as `stryker.apk`.
3. Zip the contents of this dir at archive root (module.prop, *.sh, META-INF/,
   modules/, stryker.apk) -> malachite-stryker-monitor-vX.Y.Z.zip.

Released zips live on the GitHub release (not in git — the .ko and APK are build
artifacts). Latest: v1.4.6 on release v1.1.0.
