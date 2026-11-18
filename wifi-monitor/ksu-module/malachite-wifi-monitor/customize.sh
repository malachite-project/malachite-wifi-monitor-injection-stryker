#!/system/bin/sh

fail_install() { ui_print "$1"; abort; }

[ "$(getprop ro.product.vendor.device)" = malachite ] ||
	fail_install "This helper requires the malachite vendor device."
[ "$(getprop ro.board.platform)" = mt6878 ] ||
	fail_install "This helper requires the MT6878 platform."

# Reject payloads or boot scripts carried over from the previous delivery path.
for entry in service.sh post-fs-data.sh swap.sh system; do
	[ ! -e "$MODPATH/$entry" ] || fail_install "Unexpected module entry: $entry"
done
for ko in "$MODPATH"/modules/*.ko; do
	[ ! -e "$ko" ] || fail_install "Unexpected driver payload: $ko"
done
[ ! -e "$MODPATH/tools/aireplay-ng" ] ||
	fail_install "Remove the legacy transmit tool from the package."

set_perm "$MODPATH/common.sh" 0 0 0644
set_perm "$MODPATH/action.sh" 0 0 0755
if [ -f "$MODPATH/tools/iw" ]; then
	set_perm "$MODPATH/tools/iw" 0 0 0755
fi
ui_print "Passive monitor helper installed. The Action button shows driver and interface status."
