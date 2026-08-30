# Docker + Git 操作记录（学习笔记）

> 本文档记录把本项目从**本地 → Docker 容器化 → push 到 GitHub** 全过程用到的命令，每条附"作用 + 何时用"。按操作顺序分阶段。

---

## 阶段 0：环境检查（开始前确认 Docker 装好、在跑）

```bash
# 看 Docker 版本（能出 Server 版本 = daemon 在跑；只出 Client 没出 Server = Docker Desktop 没启动）
docker version

# 列出正在跑的容器（空 = 没有容器在跑，正常）
docker ps

# 看 Docker 整体资源占用（镜像/容器/卷/缓存 各占多少磁盘）
docker system df
```

> **坑**：`docker version` 只出 Client 信息、不出 Server，说明 Docker Desktop 没启动 → 去任务栏启动它，等鲸鱼图标变绿。

---

## 阶段 1：配置国内镜像加速器（拉镜像不卡）

这一步在 **Docker Desktop 图形界面**做（不是命令）：Settings → Docker Engine → 在 JSON 里加：
```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1panel.live",
    "https://docker.nju.edu.cn"
  ]
}
```
点 **Apply & restart**。然后命令行验证：
```bash
# 看加速器是否生效（能看到上面 3 个地址 = 成功）
docker info | grep -A4 "Registry Mirrors"
```

> **为什么**：国内直接拉 Docker Hub（国外）很慢/超时。加速器相当于走国内 CDN。

---

## 阶段 2：构建镜像（把代码打包成"安装包"）

```bash
# 在项目根目录（有 docker-compose.yml 的地方）构建所有自定义镜像
docker compose build

# 如果只想看配置对不对（不真构建），校验 compose 文件
docker compose config --services      # 列出 compose 里定义的服务名
```

> **过程**：拉基础镜像（python/node/nginx）→ 装依赖（pip/npm）→ 拷代码 → 打包。
> **慢是正常的**：首次要拉镜像 + 编译依赖 + WSL2 磁盘慢，十几分钟。后续走缓存会快很多。

---

## 阶段 3：启动 / 停止 / 重启

```bash
# 启动全部服务（-d = 后台跑，detached）
docker compose up -d

# 重新构建并启动（改了 Dockerfile/compose 后用，--build = 先重建镜像再起）
docker compose up -d --build

# 停止并删除所有容器（数据卷保留 → 数据不丢）
docker compose down

# ⚠ 危险：停止 + 连数据卷一起删（数据全没！调试别手滑加 -v）
docker compose down -v

# 只重启某个服务（比如改了 agent，只想重启它）
docker compose restart agent
```

> **关键区分**：`down`（保留卷，数据在）vs `down -v`（连卷删，数据没）。日常用 `down`。

---

## 阶段 4：查看状态 / 排查问题（最常用）

```bash
# 看所有容器状态（Up = 正常；Exited/restarting = 有问题）
docker compose ps -a              # -a = 含已停止的

# 看某个服务的日志（排查崩溃/报错必看）
docker compose logs agent         # 看 agent 全部日志
docker compose logs agent --tail 30    # 只看最后 30 行
docker compose logs agent -f      # 实时跟踪日志（像 tail -f）

# 进到容器里面（像登录进那台机器，可以手动跑命令查问题）
docker compose exec agent sh      # 进 agent 容器开个 shell
# 进去之后可以：ls / cat / curl 等，exit 退出

# 在容器里跑一条命令（不进 shell）
docker compose exec agent sh -c 'echo $LLM_BASE_URL'    # 看容器里的环境变量
```

**健康检查（从主机直接 curl 各服务的健康端点）**：
```bash
curl http://localhost:8000/api/health     # backend 健康（看能否连上 agent）
curl http://localhost:8642/health         # agent 健康（agent 初始化要 ~3 分钟，别急）
curl http://localhost:8086/health         # influxdb 健康
curl -o /dev/null -w "%{http_code}" http://localhost:8080/   # frontend 返回 200 = 正常
```

> **排查思路**：先 `ps -a` 看哪个容器挂了 → `logs <服务>` 看报错 → 必要时 `exec` 进去细查。

---

## 阶段 5：镜像管理

```bash
# 列出所有镜像（自己 build 的 + 拉的官方的）
docker images

# 删某个镜像（省磁盘；删了下次 build/启动要重来）
docker rmi <镜像名或ID>

# 清理悬空/没用的小编
docker image prune -f
```

> **概念**：镜像 = 安装包（模板）；容器 = 用安装包装好跑起来的实例。一个镜像可以起多个容器。

---

## 阶段 6：数据卷管理（数据持久化）

```bash
# 列出所有数据卷
docker volume ls

# 看某个卷的详情（数据实际存在哪、什么时候建的）
docker volume inspect ecological_env_influxdb-data

# 清理没人用的孤儿卷（匿名、没容器引用的）
docker volume prune -f

# 删指定卷
docker volume rm <卷名>
```

> **概念**：容器是"一次性"的（删了重建数据没），**卷是外挂的"数据保险箱"**，容器删了卷还在。本项目 `influxdb-data` 卷存监测数据，`influxdb-config` 存数据库配置——只要不 `down -v`，数据/配置跨重启都在。

---

## 阶段 7：往 InfluxDB 导数据（一次性）

```bash
# 从主机用 venv 跑导入脚本，把 xls 数据写进 influxdb 容器
INFLUXDB_URL=http://localhost:8086 \
INFLUXDB_TOKEN=influxdb-local-token \
INFLUXDB_ORG=ecological_env \
INFLUXDB_BUCKET=monitoring-data \
ecological_env/Scripts/python.exe shared/data/import_to_influxdb.py

# 进 influxdb 容器查数据（带 token）
docker compose exec influxdb influx query \
  'from(bucket:"monitoring-data") |> range(start:2026-07-14) |> count()' \
  --org ecological_env --token influxdb-local-token
```

> **坑**：导入脚本默认超时 10s，写大批量数据会超时失败 → 改成 120s（已修）。

---

## 阶段 8：端到端测试（验证整条链路通）

```bash
# 从 backend 发一个查询，走 backend→agent→子智能体→influxdb 全链路（~60s 返回）
curl -s -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{"query":"给我7月14号pH和COD数据","session_id":"test"}'
```

> 中文 body 用 `-d` 在 Windows 上可能编码出错 → 改用 `--data-binary @文件名`（把 JSON 写到文件再传）。

---

## 阶段 9：Git 操作（提交代码到 GitHub）

### 9.1 查看状态 / 暂存 / 提交
```bash
git status                       # 看哪些文件改了/新增/删除了（工作区 vs 暂存区）
git status --short               # 简洁版（M=改 D=删 ??=新）

git diff                         # 看未暂存的具体改动
git diff --cached                # 看已暂存的改动（将要进 commit 的）

git add <文件>                   # 暂存某个文件
git add .                        # 暂存所有改动（慎用，会把无关的也带上）
git add -u                       # 暂存所有"已跟踪文件的改动/删除"（不含新文件）

git rm <文件>                    # 删除文件并暂存（删除操作进 commit）
git rm --cached <文件>           # 取消跟踪但保留本地文件（比如误提交了 .env）

git commit -m "说明"             # 把暂存区的改动提交成一个 commit
git log --oneline -5             # 看最近 5 个提交
```

### 9.2 分支 / 远程
```bash
git branch                       # 看本地分支（* 是当前）
git branch -vv                   # 看分支 + 跟踪的远程分支 + 领先/落后多少
git branch -m 旧名 新名          # 重命名当前分支（frontend-refactor → main）

git remote -v                    # 看远程仓库地址（origin 指向哪）
git remote set-url origin <URL>  # 改远程地址（比如换新仓库）

git ls-remote origin             # 看远端有哪些分支/标签（不下载，只列）
git ls-remote --heads origin     # 只看远端的分支
```

### 9.3 推送 / 拉取
```bash
git push origin main             # 把本地 main 推到远端（远端没有就新建）
git push -u origin main          # -u = 顺便设置跟踪关系（之后 git push/pull 不用写分支名）
git pull                         # 拉取远端更新并合并
git clone <URL>                  # 把远端仓库完整克隆到本地（台式机部署第一步）
```

### 9.4 .gitignore 相关
```bash
git check-ignore <文件>          # 检查某文件是否被 gitignore（输出文件名=被忽略）
git ls-files <文件>              # 检查某文件是否被 git 跟踪（空=没跟踪）
```

> **关键概念**：`.gitignore` 防止文件**被加入仓库**；`.dockerignore` 防止文件**进 Docker 镜像**。两者独立。`.env`（含密钥）两个都要排除——但 docker-compose 用 `env_file: .env` 在**启动时从本机磁盘读它注入容器**，所以不入库也能用。

---

## 阶段 10：今天实际踩坑修的 4 个 Docker 问题（对照学习）

| 问题 | 现象 | 根因 | 修法 |
|---|---|---|---|
| ① agent 崩溃重启 | `ModuleNotFoundError: hermes_constants` | 镜像没装 Hermes 框架（本地是 editable 装的） | Dockerfile 加 `pip install -e shared/framework/hermes-agent` |
| ② 数据导入失败 | `sh: Syntax error: "&&" unexpected` | compose 命令 YAML 折叠 + sh 解析炸 | 命令改 exec 数组形式 + 用 `;` 连接 |
| ③ grafana 起不来 | `port 3000 already in use` | 主机 3000 端口被占 | compose 改 `3001:3000` |
| ④ 导入写超时 | `ReadTimeoutError 9.78s` | influxdb-client 默认 10s 超时 | 脚本超时改 120s |

**通用排查套路**：`docker compose ps -a`（找挂的）→ `docker compose logs <服务>`（看报错）→ 改配置 → `docker compose up -d --build`（重建重启）→ 再验证。

---

## 台式机部署（明天用，就这 3 步）

```bash
git clone https://github.com/Nlieky/Ecological_env.git
cd Ecological_env
cp .env.example .env       # ★ 必须编辑：填台式机的 LLM_BASE_URL/LLM_API_KEY/LLM_MODEL
docker compose up --build  # 首次构建十几分钟，起来后访问 http://localhost:8080
```

**常见问题速查**：
- build 失败 `No module named 'xxx'` → 依赖没装全，看 Dockerfile/requirements
- agent 反复重启 → `docker compose logs agent` 看报错（多半是 LLM 配置/框架问题）
- 查询没数据 → influxdb 数据没导（看 influxdb-init 日志）
- 拉镜像卡 → 配 registry-mirrors（阶段 1）
- 端口冲突 → compose 里改 `端口:端口`
