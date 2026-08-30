# 知识库查找指南

## 何时使用

用户问**违规模式定义、判定标准、特征描述、法规条款原文**时（如"暗管偷排的数据特征是什么？""插瓶怎么判定？""水污染防治法第几条禁止暗管？"）。这类问题不需要实时监测数据，答案在 `shared/knowledge/` 目录下，**直接读文件回答，不调子智能体**。

## 工具选择

**分支策略**：
1. **用户直接指定了文件名**（如"读取典型违规模式.md"）→ **直接用 `read_file` 读完整路径**，不需要搜索
2. **用户只说了关键词、没指定文件** → 先 `search_files` 再 `read_file`

### 已知路径 → 直接读（快）

```
read_file(path="shared/knowledge/expert_experience/典型违规模式.md")
```

### 未知路径 → 搜索 → 读

- **搜索关键词**：用 `search_files(pattern="关键词", path="shared/knowledge")` 全文搜索。`pattern` 是 **regex**，不是 glob——`**/*` 会报错。中文字符直接搜即可。
- **读取文件**：用 `read_file(path="...")` 读取命中文件。
- **不可用工具**：MCP filesystem 工具（`mcp_filesystem_search_files` / `mcp_filesystem_list_directory` / `mcp_filesystem_read_text_file`）**全部不可用**，不要尝试。

### 搜索流程示例（用户问"暗管偷排怎么判定"）

1. `search_files(pattern="暗管", path="shared/knowledge")` → 命中 ~18 条，涉及 4+ 文件
2. `read_file("shared/knowledge/expert_experience/典型违规模式.md")` → 数据特征+识别要点+违规定性
3. `read_file("shared/knowledge/regulations/水污染防治法.md")` → 法律条款+处罚标准
4. `read_file("shared/knowledge/violation_patterns/violation_patterns.py")` → 代码化判据（可选）

回答时**引用原文**，标注来源文件路径。

## 知识库目录结构

```
shared/knowledge/
├── expert_experience/          # 专家经验库
│   ├── 典型违规模式.md          # 6 类违规模式完整定义（插瓶/暗管/稀释/篡改/虚假停产/工况造假）
│   │   # 每类含：数据特征 + 识别要点 + 违规定性（法规条款）
│   └── suspicion_rules.py       # 嫌疑判定规则代码
├── regulations/                # 法规库
│   ├── 水污染防治法.md          # 法规原文 + 违规类型对应 + 处罚标准
│   └── structured_regulations.py # 结构化法规数据
├── violation_patterns/         # 违规模式库（代码化）
│   └── violation_patterns.py    # ViolationPattern 定义 + PatternMatcher 算法
│       # 6 种模式：插瓶/稀释/数据造假/旁路排放(暗管)/采样造假/仪器篡改
└── process_knowledge/          # 工艺知识库
```

## 跨层文件对应关系

同一个违规类型在知识库中**分布在不同层级的文件里**，搜索时需要关联读取：

| 违规类型 | expert_experience | violation_patterns.py | regulations | expert_reasoner.py |
|---------|-------------------|----------------------|-------------|-------------------|
| 暗管偷排 | `典型违规模式.md` 第二节 | `BYPASS_DISCHARGE` | `水污染防治法.md` 第83条 | `secret_pipe` |
| 插瓶干扰 | `典型违规模式.md` 第一节 | `BOTTLE_INTERFERENCE` | `水污染防治法.md` 第23条 | `bottle_interference` |
| 稀释排放 | `典型违规模式.md` 第三节 | `DILUTION_DISCHARGE` | `水污染防治法.md` 第83条 | `data_dilution` |

搜索流程示例见上文「场景 B」。

## 注意

- `search_files` 的 `pattern` 参数是 **regex**，不是 glob。`**/*` 会报 regex parse error——不要用 glob 语法。
- 中文字符直接搜即可，无需转义。
- 代码文件（.py）里通常有结构化数据定义，比 Markdown 更适合程序化查询。
- 回答时优先引用 Markdown 原文（可读性好），代码文件作为补充（提供精确阈值/算法）。
- MCP 工具（`mcp_filesystem_*`、`mcp_fetch_*`、`mcp_memory_*`、`mcp_influxdb_*`）**全部不可用**（4 个 MCP Server 未启动，详见 `mcp-diagnosis.md`）——尝试调用会返回 "Tool does not exist" 错误。遇到知识库查询，只用 `search_files` + `read_file`。