#!/system/bin/sh

IFACE=wlan0
DRIVER_VERSION=/sys/module/wlan_drv_gen4m_6878/version
BOOT_ID_FILE=/proc/sys/kernel/random/boot_id
IFINDEX_FILE=/sys/class/net/wlan0/ifindex
STATEDIR=/data/adb/malachite_wifi_monitor
WIFI_SESSION="$STATEDIR/passive.session"

resolve_iw() {
	for IW in "$MODDIR/tools/iw" /system/bin/iw /vendor/bin/iw; do
		[ -x "$IW" ] && return 0
	done
	echo "An Android-native iw is required." >&2
	return 1
}

passive_driver_loaded() {
	[ "$(cat "$DRIVER_VERSION" 2>/dev/null)" = "malachite-passive-1" ]
}

wifi_off() {
	# Reject airplane-mode override states and unreadable settings.
	[ "$(settings get global wifi_on)" = 0 ]
}

iface_type() {
	info=$("$IW" dev "$IFACE" info) || return 1
	printf '%s\n' "$info" | awk '$1 == "type" {print $2}'
}

iface_down() {
	link=$(ip -o link show dev "$IFACE") || return 1
	flags=${link#*<}
	case "$flags" in
		*'>'*) ;;
		*) return 1 ;;
	esac
	[ "$flags" != "$link" ] || return 1
	flags=${flags%%>*}
	case ",$flags," in
		*,UP,*) return 1 ;;
	esac
}

session_id() {
	boot_id=$(cat "$BOOT_ID_FILE") || return 1
	ifindex=$(cat "$IFINDEX_FILE") || return 1
	[ -n "$boot_id" ] && [ -n "$ifindex" ] || return 1
	printf '%s %s\n' "$boot_id" "$ifindex"
}

prepare_action() {
	passive_driver_loaded || {
		echo "Load the audited passive driver through the test ROM first." >&2
		return 1
	}
	resolve_iw || return 1

	umask 077
	mkdir -p "$STATEDIR" && chmod 700 "$STATEDIR" || return 1
	exec 9>"$STATEDIR/passive.lock"
	flock -n 9 || {
		echo "Could not lock the monitor action." >&2
		return 1
	}
}

arm_monitor() {
	case "$1" in
		6|36) ;;
		*) echo "Supported test channels are 6 and 36." >&2; return 1 ;;
	esac
	if ! wifi_off || [ "$(iface_type)" != managed ] || ! iface_down; then
		echo "Turn off Android Wi-Fi and hotspot. The test ROM must keep a down, managed wlan0 available." >&2
		return 1
	fi
	current_session=$(session_id) || return 1
	# Record ownership before touching wlan0 so a later action can retry cleanup.
	printf '%s\n' "$current_session" > "$WIFI_SESSION" || return 1
	if ! "$IW" dev "$IFACE" set type monitor ||
	   ! ip link set dev "$IFACE" up ||
	   ! "$IW" dev "$IFACE" set channel "$1" HT20 ||
	   [ "$(iface_type)" != monitor ]; then
		echo "Monitor setup failed. Attempting to restore the interface." >&2
		disarm_monitor || echo "Recovery failed. Resolve it before enabling Android Wi-Fi." >&2
		return 1
	fi
	echo "Monitor configured on channel $1. Verify the channel from received frames."
}

disarm_monitor() {
	if ! session=$(cat "$WIFI_SESSION" 2>/dev/null) ||
	   ! current_session=$(session_id) ||
	   [ "$current_session" != "$session" ]; then
		echo "No monitor session owned by this module for the current interface." >&2
		return 1
	fi
	wifi_off || {
		echo "Turn off Android Wi-Fi before attempting monitor recovery." >&2
		return 1
	}
	case "$(iface_type)" in
		monitor)
			ip link set dev "$IFACE" down &&
				"$IW" dev "$IFACE" set type managed || return 1
			;;
		managed) ;;
		*) return 1 ;;
	esac
	[ "$(iface_type)" = managed ] && iface_down || return 1
	rm -f "$WIFI_SESSION" || return 1
	echo "wlan0 is managed and down. Android Wi-Fi can now be enabled manually."
}

status() {
	if passive_driver_loaded; then
		echo "Audited passive driver is resident."
	else
		echo "Audited passive driver is absent."
	fi
	if resolve_iw; then
		"$IW" dev "$IFACE" info
	else
		return 1
	fi
}
