#!/usr/bin/env python3
import json
import os
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ENDPOINT = "https://chatgpt.com/backend-api/wham/rate-limit-reset-credits"
BEIJING = ZoneInfo("Asia/Shanghai")
APP_TITLE = "Rate Limit Credits"


class AppError(RuntimeError):
    """An expected, user-facing application error."""


def auth_path():
    root = os.environ.get("CODEX_HOME")
    if root:
        return Path(root) / "auth.json"
    if sys.platform.startswith("linux"):
        return Path.home() / ".codex" / "auth.json"
    raise AppError("未设置 CODEX_HOME；非 Linux 系统请将它设置为包含 auth.json 的目录")


def read_token():
    path = auth_path()
    try:
        with path.open(encoding="utf-8") as stream:
            auth = json.load(stream)
    except FileNotFoundError as error:
        raise AppError(f"未找到凭证文件：{path}") from error
    except PermissionError as error:
        raise AppError(f"没有权限读取凭证文件：{path}") from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AppError("凭证文件无法读取或格式无效") from error

    if not isinstance(auth, dict):
        raise AppError("凭证文件格式无效：顶层必须是 JSON 对象")

    for key in ("tokens", "token"):
        value = auth.get(key)
        if isinstance(value, dict):
            token = value.get("access_token")
            if isinstance(token, str) and token.strip():
                return token
    raise AppError("凭证文件中没有可用 access_token")


def beijing_time(value):
    if value is None:
        return "未知"
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            parsed = datetime.fromtimestamp(
                value / (1000 if value > 10**11 else 1), timezone.utc
            )
        else:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            parsed = parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
        return parsed.astimezone(BEIJING).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OverflowError, OSError):
        return "未知"


def first(card, names):
    return next((card[name] for name in names if card.get(name) is not None), None)


def query():
    request = urllib.request.Request(
        ENDPOINT,
        headers={
            "Authorization": f"Bearer {read_token()}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise AppError("凭证失效或 Authorization header 未正确携带") from error
        raise AppError(f"请求失败（HTTP {error.code}）") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise AppError("无法连接查询服务，请检查网络后重试") from error

    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError, TypeError) as error:
        raise AppError("查询服务返回了无法解析的响应") from error

    if not isinstance(payload, dict) or "credits" not in payload:
        raise AppError("查询服务响应格式已变化，未找到 credits 字段")
    credits = payload["credits"]
    if not isinstance(credits, list):
        raise AppError("查询服务响应格式无效：credits 不是列表")

    cards = []
    for credit in credits:
        if not isinstance(credit, dict):
            continue
        cards.append((
            beijing_time(
                first(
                    credit,
                    (
                        "granted_at",
                        "issued_at",
                        "issuedAt",
                        "created_at",
                        "createdAt",
                        "start_at",
                        "startAt",
                    ),
                )
            ),
            beijing_time(
                first(
                    credit,
                    (
                        "expires_at",
                        "expiresAt",
                        "expiration_at",
                        "expirationAt",
                        "end_at",
                        "endAt",
                    ),
                )
            ),
        ))
    return status, cards


def run_gtk():
    try:
        import gi

        gi.require_version("Gdk", "3.0")
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gdk, GLib, Gtk
    except (ImportError, ValueError):
        print(
            "Rate Limit Credits: 当前 Python 没有 GTK3/PyGObject，请使用 run.sh 启动。",
            file=sys.stderr,
        )
        return 1

    css = b"""
    * { font-family: Sans; }
    window, #app-root { background-color: #0b1114; color: #ecf5f1; }
    .topbar { background-color: #10191d; border-bottom: 1px solid #223137; padding: 14px 28px; }
    .brand-mark { background-color: transparent; border-left: 2px solid #a7efd4; border-radius: 0; color: #a7efd4; font-family: Monospace; font-size: 11px; font-weight: 700; letter-spacing: 1px; padding-left: 9px; }
    .brand-name { color: #edf7f3; font-size: 13px; font-weight: 700; letter-spacing: 1px; }
    .brand-caption, .subtle, .metric-label, .card-label, .footer, .empty-copy { color: #82928e; }
    .brand-caption { font-size: 10px; letter-spacing: 1.4px; }
    .local-pill { color: #94e6c7; font-size: 10px; font-weight: 700; padding: 5px 0; }
    .server-pill { background-color: #172b28; border: 1px solid #285047; border-radius: 12px; color: #94e6c7; font-size: 10px; font-weight: 700; min-width: 64px; padding: 6px 10px; }
    .server-pill.error { background-color: #312321; border-color: #74453c; color: #ffab96; }
    .eyebrow { color: #75d7b5; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
    .hero-title { color: #f2f8f5; font-size: 27px; font-weight: 700; }
    .subtitle { color: #899a95; font-size: 12px; }
    .status-panel, .credit-row, .empty-state { background-color: #121d21; border: 1px solid #24343a; border-radius: 12px; }
    .status-panel { padding: 14px 16px; }
    .status-icon { background-color: #17372e; border-radius: 22px; color: #8df0c5; font-size: 19px; font-weight: 700; }
    .status-icon.loading { background-color: #263329; color: #d9e2b0; }
    .status-icon.error { background-color: #3b2421; color: #ffab96; }
    .status-title { color: #edf7f3; font-size: 14px; font-weight: 700; }
    .status-copy { color: #8b9c97; font-size: 11px; }
    .refresh-button, .refresh-button:hover, .refresh-button:active, .refresh-button:focus {
        background-image: none;
        background-color: #a7efd4;
        border: 1px solid #baf5df;
        border-radius: 8px;
        box-shadow: none;
        color: #10251d;
        font-size: 11px;
        font-weight: 700;
        padding: 8px 13px;
        text-shadow: none;
    }
    .refresh-button:hover { background-color: #c2f6e3; border-color: #d2f8e8; }
    .refresh-button label, .refresh-button:hover label, .refresh-button:active label, .refresh-button:focus label { color: #10251d; }
    .refresh-button:disabled, .refresh-button:disabled label { background-image: none; background-color: #29443c; border-color: #41645a; color: #9bb8ad; }
    .metric-strip { background-color: #121d21; border: 1px solid #24343a; border-radius: 10px; padding: 12px 0; }
    .metric-card { background-color: transparent; border: none; border-right: 1px solid #26373c; border-radius: 0; padding: 0 18px; }
    .metric-card:last-child { border-right: none; }
    .metric-label { font-size: 10px; letter-spacing: .5px; }
    .metric-value { color: #eff8f4; font-family: Sans; font-size: 15px; font-weight: 700; }
    .section-title { color: #eaf5f1; font-size: 18px; font-weight: 700; }
    .credit-row { padding: 12px 14px; }
    .card-number { background-color: #1c3a33; border: 1px solid #35685b; border-radius: 7px; color: #9aebcc; font-size: 11px; font-weight: 700; }
    .card-title { color: #e9f4f0; font-size: 12px; font-weight: 700; }
    .card-label { font-size: 10px; }
    .card-value { color: #c5d5cf; font-family: Monospace; font-size: 11px; }
    .expiry-value { color: #ffab94; font-family: Monospace; font-size: 11px; font-weight: 700; }
    .empty-state { padding: 22px; }
    .empty-symbol { color: #5f8880; font-size: 25px; }
    .empty-title { color: #dcebe5; font-size: 13px; font-weight: 700; }
    .empty-copy { font-size: 11px; }
    .footer { font-size: 10px; }
    scrolledwindow, viewport { background-color: transparent; border: none; }
    scrollbar trough { background-color: #0e171a; }
    scrollbar slider { background-color: #35514a; border-radius: 8px; }
    """

    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    settings = Gtk.Settings.get_default()
    if settings is not None:
        settings.set_property("gtk-application-prefer-dark-theme", True)
    screen = Gdk.Screen.get_default()
    if screen is None:
        print("Rate Limit Credits: 当前没有可用的图形会话。", file=sys.stderr)
        return 1
    Gtk.StyleContext.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    class CreditsWindow(Gtk.Window):
        def __init__(self):
            super().__init__(title=APP_TITLE)
            self.set_default_size(900, 620)
            self.set_size_request(720, 500)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.connect("destroy", Gtk.main_quit)
            self.busy = False
            self._build()
            self.show_all()
            self.refresh()

        @staticmethod
        def label(text, style=None, xalign=0.0):
            widget = Gtk.Label(label=text, xalign=xalign)
            if style:
                widget.get_style_context().add_class(style)
            return widget

        @staticmethod
        def add_class(widget, name):
            widget.get_style_context().add_class(name)

        @staticmethod
        def remove_class(widget, name):
            widget.get_style_context().remove_class(name)

        def _build(self):
            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            root.set_name("app-root")
            self.add(root)

            topbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            self.add_class(topbar, "topbar")
            root.pack_start(topbar, False, False, 0)
            mark = self.label("RLC", "brand-mark", 0.0)
            mark.set_size_request(42, 28)
            topbar.pack_start(mark, False, False, 0)
            brand = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            brand.pack_start(
                self.label("RATE LIMIT CREDITS", "brand-name"), False, False, 0
            )
            brand.pack_start(
                self.label("LOCAL QUERY", "brand-caption"), False, False, 0
            )
            topbar.pack_start(brand, False, False, 0)
            self.local_pill = self.label("●  本地凭证", "local-pill", 0.5)
            topbar.pack_end(self.local_pill, False, False, 0)

            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            content.set_margin_top(26)
            content.set_margin_bottom(20)
            content.set_margin_start(32)
            content.set_margin_end(32)
            root.pack_start(content, True, True, 0)
            content.pack_start(
                self.label("CREDENTIAL MONITOR", "eyebrow"), False, False, 0
            )
            title = self.label("重置卡来，卡来!", "hero-title")
            title.set_margin_top(7)
            content.pack_start(title, False, False, 0)
            subtitle = self.label(
                "本机查询 rate-limit reset credits，时间统一显示为北京时间。",
                "subtitle",
            )
            subtitle.set_margin_top(8)
            content.pack_start(subtitle, False, False, 0)

            self.status_panel = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=14
            )
            self.add_class(self.status_panel, "status-panel")
            self.status_panel.set_margin_top(20)
            content.pack_start(self.status_panel, False, False, 0)
            self.status_icon = self.label("…", "status-icon", 0.5)
            self.status_icon.set_size_request(44, 44)
            self.status_panel.pack_start(self.status_icon, False, False, 0)
            status_copy = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            status_copy.set_valign(Gtk.Align.CENTER)
            self.status_panel.pack_start(status_copy, True, True, 0)
            self.status_title = self.label("正在检查凭证", "status-title")
            self.status_text = self.label(
                "准备查询 rate-limit reset credits", "status-copy"
            )
            self.status_text.set_line_wrap(True)
            status_copy.pack_start(self.status_title, False, False, 0)
            status_copy.pack_start(self.status_text, False, False, 0)
            actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            actions.set_valign(Gtk.Align.CENTER)
            self.status_panel.pack_end(actions, False, False, 0)
            self.server_pill = self.label("CHECKING", "server-pill", 0.5)
            actions.pack_start(self.server_pill, False, False, 0)
            self.refresh_button = Gtk.Button(label="↻  刷新")
            self.add_class(self.refresh_button, "refresh-button")
            self.refresh_button.set_relief(Gtk.ReliefStyle.NONE)
            self.refresh_button.set_tooltip_text("重新查询额度")
            self.refresh_button.connect("clicked", self.refresh)
            actions.pack_start(self.refresh_button, False, False, 0)

            metrics = Gtk.Grid(column_spacing=0)
            self.add_class(metrics, "metric-strip")
            metrics.set_column_homogeneous(True)
            metrics.set_margin_top(14)
            content.pack_start(metrics, False, False, 0)
            self.count_value = self._metric(metrics, 0, "当前重置卡", "—")
            self._metric(metrics, 1, "时区", "北京时间  UTC+8")
            self.checked_value = self._metric(metrics, 2, "上次查询", "—")

            heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            heading.set_margin_top(22)
            heading.set_margin_bottom(9)
            content.pack_start(heading, False, False, 0)
            heading.pack_start(
                self.label("重置卡明细", "section-title"), False, False, 0
            )
            self.card_hint = self.label("等待查询", "subtle")
            heading.pack_end(self.card_hint, False, False, 0)

            self.scroller = Gtk.ScrolledWindow()
            self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            content.pack_start(self.scroller, True, True, 0)
            self.card_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.scroller.add(self.card_list)
            footer = self.label(
                "凭证只在本机进程内使用，不会显示 token、cookie 或唯一 ID。",
                "footer",
                0.5,
            )
            footer.set_margin_top(18)
            content.pack_start(footer, False, False, 0)

        def _metric(self, grid, column, label_text, value_text):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            self.add_class(card, "metric-card")
            card.set_hexpand(True)
            grid.attach(card, column, 0, 1, 1)
            card.pack_start(self.label(label_text, "metric-label"), False, False, 0)
            value = self.label(value_text, "metric-value")
            card.pack_start(value, False, False, 0)
            return value

        def _set_status(self, mode, icon, title, text, pill):
            for widget in (self.status_icon, self.server_pill):
                for name in ("loading", "error"):
                    self.remove_class(widget, name)
            if mode in ("loading", "error"):
                self.add_class(self.status_icon, mode)
            if mode == "error":
                self.add_class(self.server_pill, "error")
            self.status_icon.set_text(icon)
            self.status_title.set_text(title)
            self.status_text.set_text(text)
            self.server_pill.set_text(pill)

        def refresh(self, *_args):
            if self.busy:
                return
            self.busy = True
            self.refresh_button.set_sensitive(False)
            self.refresh_button.set_label("⟳  查询中")
            self.card_hint.set_text("查询中")
            self._set_status(
                "loading",
                "…",
                "正在检查凭证",
                "正在请求 rate-limit reset credits",
                "CHECKING",
            )
            self._render_empty("…", "正在读取额度", "网络请求完成后会显示最新结果。")
            threading.Thread(target=self._query_worker, daemon=True).start()

        def _query_worker(self):
            try:
                status, cards = query()
                GLib.idle_add(self._show_success, status, cards)
            except AppError as error:
                GLib.idle_add(self._show_error, str(error))
            except Exception as error:
                GLib.idle_add(
                    self._show_error, f"程序运行失败（{type(error).__name__}）"
                )

        def _finish(self):
            self.busy = False
            self.refresh_button.set_sensitive(True)
            self.refresh_button.set_label("↻  刷新")

        def _show_success(self, status, cards):
            self._finish()
            checked = datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M:%S")
            self._set_status(
                "ok",
                "✓",
                "凭证有效，查询成功",
                f"HTTP {status}  ·  发现 {len(cards)} 张重置卡",
                f"HTTP {status}",
            )
            self.count_value.set_text(str(len(cards)))
            self.checked_value.set_text(checked)
            self.card_hint.set_text(f"{len(cards)} 张卡片")
            self._render_cards(cards)
            return False

        def _show_error(self, message):
            self._finish()
            self._set_status("error", "!", "查询未完成", message, "ERROR")
            self.count_value.set_text("—")
            self.card_hint.set_text("需要处理")
            self._render_empty(
                "!", "暂时无法显示重置卡", "修复状态后点击刷新重新查询。"
            )
            return False

        def _render_empty(self, symbol, title, copy):
            self._clear_cards()
            empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            self.add_class(empty, "empty-state")
            empty.pack_start(self.label(symbol, "empty-symbol", 0.5), False, False, 0)
            empty.pack_start(self.label(title, "empty-title", 0.5), False, False, 0)
            empty.pack_start(self.label(copy, "empty-copy", 0.5), False, False, 0)
            self.card_list.pack_start(empty, False, False, 0)
            self.card_list.show_all()

        def _clear_cards(self):
            for child in self.card_list.get_children():
                self.card_list.remove(child)

        def _render_cards(self, cards):
            self._clear_cards()
            if not cards:
                self._render_empty(
                    "∅",
                    "当前没有重置卡",
                    "查询结果中没有可用的 rate-limit reset credits。",
                )
                return
            for index, (issued, expires) in enumerate(cards, 1):
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
                self.add_class(row, "credit-row")
                badge = self.label(str(index), "card-number", 0.5)
                badge.set_size_request(36, 36)
                row.pack_start(badge, False, False, 0)
                detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                detail.set_hexpand(True)
                row.pack_start(detail, True, True, 0)
                detail.pack_start(
                    self.label("RATE LIMIT RESET CREDIT", "card-title"), False, False, 0
                )
                times = Gtk.Grid(column_spacing=30)
                times.set_column_homogeneous(True)
                detail.pack_start(times, False, False, 0)
                issued_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                times.attach(issued_box, 0, 0, 1, 1)
                issued_box.pack_start(
                    self.label("发放时间", "card-label"), False, False, 0
                )
                issued_box.pack_start(self.label(issued, "card-value"), False, False, 0)
                expiry_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                times.attach(expiry_box, 1, 0, 1, 1)
                expiry_box.pack_start(
                    self.label("过期时间 · 北京时间", "card-label"), False, False, 0
                )
                expiry_box.pack_start(
                    self.label(expires, "expiry-value"), False, False, 0
                )
                self.card_list.pack_start(row, False, False, 0)
            self.card_list.show_all()

    try:
        CreditsWindow()
        Gtk.main()
    except Exception as error:
        print(
            f"{APP_TITLE}: 无法启动 GTK 窗口（{type(error).__name__}）", file=sys.stderr
        )
        return 1
    return 0


def main():
    return run_gtk()


if __name__ == "__main__":
    raise SystemExit(main())
