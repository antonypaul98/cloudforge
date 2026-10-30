#!/bin/sh
# Fixed first-party Linux namespace fixture only. Not a general code sandbox.
set -eu
root="$1"
source_dir="$2"

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
chmod 0444 "$root/app/app.py" "$root/app/observer.py"
ip link set lo up
exec chroot "$root" /usr/bin/python3 -I -S /app/observer.py
