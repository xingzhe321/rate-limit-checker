# Rate Limit Credits

一个原生 GTK 桌面小工具，用于查询 Codex 的 rate-limit reset credits。

> 纯 Vibe Coding 产物。
<img width="901" height="657" alt="image" src="https://github.com/user-attachments/assets/ad80120d-b4cd-4d9a-a8b0-7943545ea256" />

## Features

- 自动读取本机 Codex 凭证
- 显示重置卡发放时间和过期时间
- UTC 自动转换为北京时间（UTC+8）
- 支持刷新、加载、错误和空数据状态
- 凭证只在本机进程内使用，不显示 token、cookie 或唯一 ID

## Run

```bash
./run.sh
```

Linux 未设置 `CODEX_HOME` 时默认读取 `~/.codex/auth.json`。其他系统请将 `CODEX_HOME` 设置为包含 `auth.json` 的目录。

安装到当前用户的应用菜单：

```bash
./install.sh
```

安装后可以在系统应用菜单中搜索 `Rate Limit Credits`。

## Requirements

- Python 3
- GTK 3
- PyGObject

应用会优先使用 `HTTP_PROXY`、`HTTPS_PROXY` 等环境变量；Linux GNOME 应用菜单启动时，如果没有继承这些变量，会自动读取 GNOME 的手动 HTTP/HTTPS 代理设置。

仓库中的 `RateLimitCredits.desktop` 适合通过 `gio launch` 启动；文件管理器可能会把它当作文本文件打开。

> 注意：`.desktop` 文件不是 Shell 脚本，不要选择“右键 → 作为程序运行”。如果文件管理器没有识别它，请先允许启动，或运行：

```bash
gio launch ./RateLimitCredits.desktop
```

需要在终端中直接启动时，使用：

```bash
./run.sh
```
