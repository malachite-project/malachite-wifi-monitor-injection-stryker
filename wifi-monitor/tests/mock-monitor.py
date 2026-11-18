import fcntl
import os
from pathlib import Path
import subprocess
import tempfile

source = Path(__file__).resolve().parents[1] / 'ksu-module/malachite-wifi-monitor'
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    paths = {'/sys/module/wlan_drv_gen4m_6878/version': 'version',
             '/proc/sys/kernel/random/boot_id': 'boot',
             '/sys/class/net/wlan0/ifindex': 'ifindex',
             '/data/adb/malachite_wifi_monitor': 'state'}
    common = (source / 'common.sh').read_text()
    for absolute, relative in paths.items():
        common = common.replace(absolute, str(root / relative))
    (root / 'common.sh').write_text(common)
    (root / 'action.sh').write_bytes((source / 'action.sh').read_bytes())
    (root / 'tools').mkdir()
    commands = {
        'tools/iw': '''case "$3" in
info)
    [ ! -f absent ] || exit 1
    printf 'Interface wlan0\n\ttype %s\n' "$(cat type)" ;;
set)
    echo "iw $*" >> trace
    case "$4" in
        type) [ "$(cat fail)" != "$5" ] || exit 1; echo "$5" > type ;;
        channel) [ "$(cat fail)" != channel ] ;;
    esac ;;
esac''',
        'ip': '''case "$1" in
-o) [ ! -f absent ] || exit 1; printf '3: wlan0: <%s> mtu 1500\n' "$(cat flags)" ;;
link)
    echo "ip $*" >> trace
    [ "$(cat fail)" != "$5" ] || exit 1
    case "$5" in up) echo BROADCAST,UP > flags ;; down) echo BROADCAST > flags ;; esac ;;
esac''',
        'settings': '''[ "$(cat wifi)" != error ] || exit 1
cat wifi''',
        'getprop': '''case "$1" in
ro.product.vendor.device) cat device ;;
ro.board.platform) cat platform ;;
esac''',
    }
    for file, body in commands.items():
        path = root / file
        path.write_text('#!/bin/sh\n' + body + '\n')
        path.chmod(0o755)
    env = dict(os.environ, PATH=f'{root}:' + os.environ['PATH'])
    def put(name, value):
        (root / name).write_text(value + '\n')
    def prepare():
        for name, value in {'version': 'malachite-passive-1', 'boot': 'test-boot',
                            'ifindex': '3', 'type': 'managed', 'flags': 'BROADCAST',
                            'fail': '', 'wifi': '0', 'trace': ''}.items():
            put(name, value)
        for name in ['state/passive.session', 'absent']:
            (root / name).unlink(missing_ok=True)
    def run(*args, expected=0):
        result = subprocess.run(['dash', str(root/'action.sh'), *args], cwd=root,
                                env=env, capture_output=True, text=True)
        assert result.returncode == expected, (args, result.returncode, result.stdout, result.stderr)
        return result
    def unchanged():
        assert not (root/'trace').read_text().strip()
    def managed():
        assert (root/'type').read_text().strip() == 'managed'
        assert (root/'flags').read_text().strip() == 'BROADCAST'
        assert not (root/'state/passive.session').exists()
    prepare()
    assert 'resident' in run().stdout
    unchanged()
    for _ in range(5):
        for channel in ('6', '36'):
            run('arm', channel)
            assert (root/'type').read_text().strip() == 'monitor'
            run('disarm')
            managed()
    print('PASS status and ten arm/disarm cycles across both channels')
    for name, value in [('wifi','1'), ('wifi','2'), ('wifi','error'),
                        ('version','stock'), ('type','AP'), ('flags','UP,BROADCAST')]:
        prepare()
        put(name, value)
        run('arm', '6', expected=1)
        unchanged()
    prepare()
    put('absent', '')
    run('arm', '6', expected=1)
    run(expected=1)
    unchanged()
    prepare()
    run('arm', '0', expected=1)
    run('arm', '999', expected=1)
    run('invalid', expected=1)
    unchanged()
    print('PASS unsupported state, identity, input and missing-interface gates')
    for stage in ('monitor', 'up', 'channel'):
        prepare()
        put('fail', stage)
        run('arm', '6', expected=1)
        managed()
    print('PASS recovery after each failed arm command')
    for stage in ('down', 'managed'):
        prepare()
        run('arm', '6')
        put('fail', stage)
        run('disarm', expected=1)
        assert (root/'state/passive.session').exists()
        put('fail','')
        run('disarm')
        managed()
    for name in ('boot', 'ifindex', 'wifi'):
        prepare()
        run('arm','6')
        put('trace','')
        put(name,'99')
        run('disarm',expected=1)
        unchanged()
    prepare()
    (root/'state').mkdir(exist_ok=True)
    with open(root/'state/passive.lock','w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run('arm','6',expected=1)
    unchanged()
    print('PASS retryable recovery, stale ownership and concurrent action rejection')

    installer = root/'install.sh'
    installer.write_text('ui_print() { echo "$*"; }\nabort() { exit 9; }\nset_perm() { :; }\n' +
                         (source/'customize.sh').read_text())
    env['MODPATH'] = str(root)
    put('device','malachite')
    put('platform','mt6878')
    def install(expected):
        result = subprocess.run(['dash', str(installer)], cwd=root, env=env,
                                capture_output=True, text=True)
        assert result.returncode == expected, (result.returncode, result.stdout, result.stderr)
    install(0)
    for name in ('service.sh', 'post-fs-data.sh', 'swap.sh', 'system',
                 'modules/legacy.ko', 'tools/aireplay-ng'):
        p = root/name
        p.parent.mkdir(exist_ok=True)
        p.touch()
        install(9)
        p.unlink()
    put('platform','other')
    install(9)
    put('platform','mt6878')
    put('device','other')
    install(9)
    print('PASS install accepts helper and rejects legacy entries and wrong hardware')
