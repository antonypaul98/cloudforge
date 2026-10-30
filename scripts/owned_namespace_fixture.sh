#!/bin/sh
# Fixed first-party Linux namespace fixture only. Not a general code sandbox.
set -eu
root="$1"
source_dir="$2"
expected_app_sha="$3"
expected_observer_sha="$4"

# Verify staged bytes before any mount or process launch. The hashes are
# supplied by the trusted parent for this fixed first-party fixture only;
# they are not independent authorization or signed provenance.
verify_digest() {
    output=$(sha256sum "$1") || exit 1
    actual=${output%% *}
    [ "$actual" = "$2" ] || exit 1
}
verify_digest "$source_dir/app.py" "$expected_app_sha"
verify_digest "$source_dir/observer.py" "$expected_observer_sha"

# This process is already inside private user, network, mount and PID namespaces.
mount --make-rprivate /
mount -t tmpfs -o size=64m,mode=0700 tmpfs "$root"
mkdir -p "$root/usr" "$root/lib" "$root/lib64" "$root/app" "$root/dev" "$root/tmp"
for path in /usr /lib /lib64; do
    mount --rbind "$path" "$root$path"
    mount -o remount,bind,ro "$root$path"
done
touch "$root/dev/null"
mount --bind /dev/null "$root/dev/null"
cp "$source_dir/app.py" "$root/app/app.py"
cp "$source_dir/observer.py" "$root/app/observer.py"
# Check the actual copied bytes as well, before entering chroot.
verify_digest "$root/app/app.py" "$expected_app_sha"
verify_digest "$root/app/observer.py" "$expected_observer_sha"
chmod 0444 "$root/app/app.py" "$root/app/observer.py"
ip link set lo up
exec chroot "$root" /usr/bin/python3 -I -S /app/observer.py
