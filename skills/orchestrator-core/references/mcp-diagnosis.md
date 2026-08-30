# MCP 工具诊断报告（2026-08-30）

## 状态：4 个 MCP Server 全部未启动

## 配置位置

`E:\project\Ecological_env\config.yaml`（**不是** `~/.hermes/config.yaml`——项目根目录下）

## 已配置的 MCP Server

| Name | 包名 | 用途 |
|------|-----|------|
| fetch | `@kazuph/mcp-fetch` | 网页抓取、图片提取 |
| memory | `@modelcontextprotocol/server-memory` | 知识图谱持久化 |
| filesystem | `@modelcontextprotocol/server-filesystem` | 文件系统访问（挂载 `shared/knowledge`） |
| influxdb | `influxdb-mcp-server` | InfluxDB 查询/写入 |

## 根因

**Node.js 安装在 `E:\nodejs\`**，`npx.cmd` 和 `npm.cmd` 存在且可用。但：

1. **config.yaml 写 `command: npx`**——Hermes 用 subprocess 启动 MCP，Windows 下 `npx` 是 `.cmd` 批处理文件，subprocess 不经过 PATHEXT 解析，找不到 `npx`（报 `FileNotFoundError: [WinError 2]`）
2. **npm 全局包在 `D:\nodejs\npm-global`**，与 Node.js 本体（`E:\nodejs`）分离，npx `-y` 自动下载的 MCP 包从未安装过

## 修复方案

**方案 A（推荐）：改 command 为绝对路径**

把 config.yaml 每个 MCP server 的 `command: npx` 改为 `command: E:\nodejs\npx.cmd`

**方案 B：修复 PATH + PATHEXT**

确保 Hermes 进程继承的 PATH 包含 `E:\nodejs` 且 PATHEXT 包含 `.CMD`

**方案 C：改用 Python 原生替代**

- InfluxDB：已有 `backend/services/influxdb_data_loader.py` + 数据感知子智能体
- 文件系统：Hermes 原生 `read_file` / `search_files` 已够用
- Memory：知识图谱功能暂不必需

## 当前影响

- `mcp_filesystem_search_files`、`mcp_filesystem_read_text_file` 等工具**出现在工具列表但调用返回 "Tool does not exist"**
- `mcp_fetch_*` 工具同样不可用
- 知识库查询只能用 Hermes 原生 `search_files` + `read_file`
- InfluxDB 查询只能通过子智能体①（数据感知），不能直接调 MCP

## 诊断方法

下次排查 MCP 配置时：
1. `read_file(config.yaml)` 看 mcp_servers 段
2. 检查 `npx` 可执行性：`shutil.which('npx')` 或 `subprocess.run(['npx', '--version'])`
3. 检查 npm 全局包目录：`npm list -g --depth=0`
4. 确认 INFLUXDB_TOKEN 环境变量：`.env` 文件中