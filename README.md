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

## Requirements

- Python 3
- GTK 3
- PyGObject

也可以在桌面环境中启动 `RateLimitCredits.desktop`。
