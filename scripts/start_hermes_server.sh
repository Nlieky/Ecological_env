#!/bin/bash
# ========================================
# Hermes API Server 启动脚本
# ========================================

echo "========================================"
echo "启动 Hermes API Server - 废水监测系统"
echo "========================================"
echo ""

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 关键配置：设置 HERMES_HOME 指向主智能体目录
export HERMES_HOME="$PROJECT_ROOT/workspace"

# API Server 配置
export API_SERVER_KEY=admin123456
export API_SERVER_PORT=8642
export API_SERVER_HOST=127.0.0.1
export GATEWAY_ALLOW_ALL_USERS=true

echo "========================================"
echo "配置信息"
echo "========================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo ""
echo "主智能体 (HERMES_HOME):"
echo "   $HERMES_HOME"
echo ""
echo "API Server:"
echo "   端口: $API_SERVER_PORT"
echo "   主机: $API_SERVER_HOST"
echo ""
echo "主智能体文件:"
echo "   配置: $HERMES_HOME/config.yaml"
echo "   身份: $HERMES_HOME/SOUL.md"
echo "   规范: $HERMES_HOME/AGENTS.md"
echo "   记忆: $HERMES_HOME/MEMORY.md"
echo ""
echo "子智能体位置:"
echo "   - $PROJECT_ROOT/subagents/multi-dimensional-data-perception-agent"
echo "   - $PROJECT_ROOT/subagents/anomaly-detection-agent"
echo "   - $PROJECT_ROOT/subagents/rule-reasoning-agent"
echo "   - $PROJECT_ROOT/subagents/disposition-execution-agent"
echo ""
echo "========================================"
echo "启动中..."
echo "========================================"
echo ""

# 使用虚拟环境中的 hermes-agent
# 不需要 cd 到外部目录，直接运行
python -m gateway.run
