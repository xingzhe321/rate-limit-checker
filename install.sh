#!/usr/bin/env sh
set -eu

APP_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
APPLICATIONS_DIR="$DATA_HOME/applications"
TARGET="$APPLICATIONS_DIR/rate-limit-credits.desktop"

mkdir -p "$APPLICATIONS_DIR"

escape_exec_path() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/%/%%/g'
}

RUN_PATH=$(escape_exec_path "$APP_DIR/run.sh")

{
    printf '%s\n' '[Desktop Entry]'
    printf '%s\n' 'Type=Application'
    printf '%s\n' 'Name=Rate Limit Credits'
    printf '%s\n' 'Comment=查询本机 Codex rate-limit reset credits'
    printf 'Exec="%s"\n' "$RUN_PATH"
    printf '%s\n' 'Terminal=false'
    printf '%s\n' 'Categories=Utility;'
    printf '%s\n' 'Keywords=Codex;credits;rate limit;'
    printf '%s\n' 'StartupNotify=true'
} > "$TARGET"

chmod 755 "$TARGET"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
fi

printf '已安装应用菜单启动器：%s\n' "$TARGET"
printf '%s\n' '现在可以在系统应用菜单中搜索 Rate Limit Credits。'
