Build artifacts — NOT committed. Drop the AArch64 driver .ko files here when
packaging the flashable zip:
  cfg80211.ko
  wlan_drv_gen4m_6878.ko   (vermagic 6.1.167)
Built from ../patches (see ../patches/BUILD.md). post-fs-data.sh bind-mounts
them over the stock driver with a fail-safe that restores stock on failure.
