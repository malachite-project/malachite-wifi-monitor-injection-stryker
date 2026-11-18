#!/system/bin/sh

MODDIR=${0%/*}
. "$MODDIR/common.sh"

case "${1:-status}" in
	status)
		echo "Use action.sh arm 6, action.sh arm 36, or action.sh disarm from a root shell."
		status
		;;
	arm)
		prepare_action && arm_monitor "${2:-6}"
		;;
	disarm)
		prepare_action && disarm_monitor
		;;
	*)
		echo "Usage: action.sh [status | arm {6|36} | disarm]" >&2
		exit 1
		;;
esac
