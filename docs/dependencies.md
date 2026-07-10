# 依赖说明

使用这个 Skill 前，请从 workspace 根目录运行依赖检查。`skills/architecture_4-1/verify_dependencies.py` 只检查用户环境中的外部运行前提，不是仓库完整性或渲染器自测工具。

## 必需与可选依赖

| 依赖 | 必需性 | 用途与边界 |
| --- | --- | --- |
| Python 及 `pillow` | 必需 | 处理 PNG 导出结果；脚本只验证 `PIL` 能否导入，不检查 Python 版本或 Pillow 的全部功能。 |
| Python 包 `playwright` | 必需 | 驱动浏览器执行 draw.io 导出；脚本验证包可导入。 |
| Playwright Chromium | 必需 | 实际启动 headless Chromium；仅安装 Python 包还不够。 |
| 本地 draw.io webapp | 条件可选 | 导出器可优先使用本地 webapp；`verify_dependencies.py` 当前只探测 `~/.vscode/extensions/hediet.vscode-drawio-1.9.0/drawio/src/main/webapp/index.html`。 |
| `https://embed.diagrams.net/` 网络访问 | 条件可选 | 没有被检查脚本识别的本地 webapp 时作为远程回退。默认检查只给出 `WARN`；加 `--check-network` 才对该 URL 发起 HEAD 请求。 |

本地 draw.io webapp 与远程 diagrams.net embed 至少需要一条可用路径。网络不是无条件必需：本地运行环境可用时，`--check-network` 不会再探测远程地址。

## 检查命令

以下命令都从 **workspace 根目录**运行：

```powershell
python skills/architecture_4-1/verify_dependencies.py
```

当本地 draw.io webapp 未被识别，并且需要确认远程回退是否可访问时：

```powershell
python skills/architecture_4-1/verify_dependencies.py --check-network
```

如果 Chromium 缺失，通常可从 workspace 根目录运行：

```powershell
python -m playwright install chromium
```

## 脚本实际检查范围

`verify_dependencies.py` 依次检查：

1. `PIL`（`pillow`）能否导入。
2. `playwright` 能否导入。
3. Playwright Chromium 能否以 headless 模式启动并关闭。
4. 固定 VS Code 扩展路径下的本地 draw.io `index.html` 是否存在。
5. 仅当本地文件不存在且传入 `--check-network` 时，`https://embed.diagrams.net/` 的 HEAD 请求是否成功。

`PASS` 表示该项探测成功；`FAIL` 会令脚本以非零状态退出。未传 `--check-network` 且本地 webapp 不存在时会显示 `WARN`，脚本不会因此失败，因为实际导出仍可能使用远程回退。

## 它不会检查什么

该脚本明确**不检查**：

- `SKILL.md`、`references/`、脚本、测试 fixture 或参考图是否齐全、是否被修改。
- 中间 JSON 是否符合 DSL，`.drawio` XML 是否有效，渲染器 self-test 或测试是否通过。
- `.tmp/` 的写权限、磁盘空间、代理、证书、DNS、防火墙或远程站点的完整浏览器交互。
- 本地 webapp 是否完整可执行；存在 `index.html` 就会通过该项。
- 真实模型的端到端渲染、PNG 是否非空、布局或视觉质量。
- Python、Pillow、Playwright、Chromium 或 draw.io webapp 的具体版本兼容性（除打印可获得的包版本外）。

因此，依赖检查通过后仍需按[使用方式](./usage.md)运行渲染和视觉验证命令；不能把依赖检查结果当成交付验收结果。

## 失败后的修复方向

- `pillow` 或 `playwright` 导入失败：在当前 Python 环境安装对应包后重跑检查。
- Chromium 启动失败：运行 `python -m playwright install chromium`，并根据报错处理系统运行库或执行权限。
- 本地 webapp 未找到：安装脚本所识别版本的 VS Code draw.io 扩展，或确保可访问远程 embed。
- 远程 HEAD 检查失败：检查代理、证书、DNS 和防火墙；也可改用可用的本地 draw.io webapp。
