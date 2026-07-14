#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

old_ifs=$IFS
IFS=:
for directory in $PATH; do
    [ -n "$directory" ] || directory=.
    candidate="$directory/python3"
    if [ -x "$candidate" ] && "$candidate" -c 'import gi; gi.require_version("Gtk", "3.0")' >/dev/null 2>&1; then
        IFS=$old_ifs
        exec "$candidate" "$SCRIPT_DIR/app.py" "$@"
    fi
done
IFS=$old_ifs

echo "Rate Limit Credits: 未找到带 GTK3/PyGObject 的 Python 3，请安装系统 GTK Python 绑定。" >&2
exit 1
