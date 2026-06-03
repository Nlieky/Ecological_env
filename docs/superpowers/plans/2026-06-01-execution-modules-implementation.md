# 研判预警与处置执行模块实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现行动执行和报告生成功能，完成从违规识别到处置执行的闭环。

**Architecture:** 采用接口抽象设计，action_executor 实现多渠道推送（监管平台、飞书、本地归档），report_generator 生成预警、汇总和趋势报告。

**Tech Stack:** Python 3.10+, ABC 抽象基类, dataclasses, typing, pytest

---

## 文件结构概览

### 新增文件

```
subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/
├── action_executor.py
└── report_generator.py

tests/subagents/
├── test_action_executor.py
└── test_report_generator.py

shared/configs/
└── disposition_config.yaml
```

### 修改文件

```
subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/__init__.py
```

---

## 阶段1: action_executor.py 实现

### Task 1.1: 创建推送渠道抽象基类和数据结构

**Files:**
- Create: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py`

- [ ] **Step 1: 编写测试 - ExecutionResult 数据类**

```python
# tests/subagents/test_action_executor.py
import pytest
from datetime import datetime
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "subagents" / "disposition-execution-agent" / "skills" / "disposition-execution-core" / "scripts"))

from action_executor import ExecutionResult


def test_execution_result_creation():
    """测试 ExecutionResult 创建"""
    result = ExecutionResult(
        success=True,
        channel="test",
        message="Test message"
    )
    
    assert result.success is True
    assert result.channel == "test"
    assert result.message == "Test message"
    assert result.error is None
    assert isinstance(result.timestamp, str)


def test_execution_result_failure():
    """测试 ExecutionResult 失败状态"""
    result = ExecutionResult(
        success=False,
        channel="test",
        message="Failed",
        error="Connection error"
    )
    
    assert result.success is False
    assert result.error == "Connection error"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_action_executor.py::test_execution_result_creation -v
```

Expected: FAIL - "ModuleNotFoundError: No module named 'action_executor'"

- [ ] **Step 3: 实现 ExecutionResult 和 PushChannel**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py
"""
行动执行模块 - 多渠道推送工单和报告
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    channel: str
    message: str
    data: Any = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PushChannel(ABC):
    """推送渠道抽象基类"""
    
    @abstractmethod
    def execute(self, work_order: Dict[str, Any]) -> ExecutionResult:
        """执行推送操作
        
        Args:
            work_order: 工单数据
            
        Returns:
            ExecutionResult: 执行结果
        """
        pass
    
    @abstractmethod
    def get_channel_name(self) -> str:
        """获取渠道名称"""
        pass
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_action_executor.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py tests/subagents/test_action_executor.py
git commit -m "feat: add ExecutionResult and PushChannel base class"
```

---

### Task 1.2: 实现 LocalArchive 推送渠道

**Files:**
- Modify: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py`

- [ ] **Step 1: 编写测试 - LocalArchive**

```python
# tests/subagents/test_action_executor.py (追加)
import tempfile
import os

def test_local_archive_execute():
    """测试本地归档推送"""
    from action_executor import LocalArchive
    
    # 使用临时目录
    temp_dir = tempfile.mkdtemp()
    archive = LocalArchive(output_dir=temp_dir)
    
    work_order = {
        "id": "WO-20260601-001",
        "alert_level": "serious",
        "violation_type": "稀释排放",
        "generated_at": "2026-06-01T10:00:00"
    }
    
    result = archive.execute(work_order)
    
    assert result.success is True
    assert result.channel == "archive"
    assert "file_path" in result.data
    assert os.path.exists(result.data["file_path"])


def test_local_archive_file_content():
    """测试归档文件内容"""
    from action_executor import LocalArchive
    
    temp_dir = tempfile.mkdtemp()
    archive = LocalArchive(output_dir=temp_dir)
    
    work_order = {
        "id": "WO-20260601-002",
        "alert_level": "moderate"
    }
    
    result = archive.execute(work_order)
    
    # 读取文件内容验证
    with open(result.data["file_path"], 'r') as f:
        content = json.load(f)
    
    assert content["id"] == "WO-20260601-002"
    assert content["alert_level"] == "moderate"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_action_executor.py::test_local_archive_execute -v
```

Expected: FAIL - "LocalArchive not found"

- [ ] **Step 3: 实现 LocalArchive 类**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py (追加)
class LocalArchive(PushChannel):
    """本地归档推送渠道"""
    
    def __init__(self, output_dir: str = "/shared/outputs/work_orders/"):
        self.output_dir = output_dir
    
    def execute(self, work_order: Dict[str, Any]) -> ExecutionResult:
        """执行本地归档"""
        try:
            from pathlib import Path
            
            # 确保输出目录存在
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            work_order_id = work_order.get("id", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{work_order_id}_{timestamp}.json"
            file_path = output_path / filename
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(work_order, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Work order archived to {file_path}")
            
            return ExecutionResult(
                success=True,
                channel=self.get_channel_name(),
                message=f"工单已归档到 {filename}",
                data={"file_path": str(file_path)}
            )
            
        except Exception as e:
            logger.error(f"Failed to archive work order: {e}")
            return ExecutionResult(
                success=False,
                channel=self.get_channel_name(),
                message="归档失败",
                error=str(e)
            )
    
    def get_channel_name(self) -> str:
        return "archive"
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_action_executor.py::test_local_archive_execute -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py tests/subagents/test_action_executor.py
git commit -m "feat: implement LocalArchive push channel"
```

---

### Task 1.3: 实现 FeishuPush 推送渠道

**Files:**
- Modify: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py`

- [ ] **Step 1: 编写测试 - FeishuPush**

```python
# tests/subagents/test_action_executor.py (追加)
from unittest.mock import patch, MagicMock

def test_feishu_push_execute():
    """测试飞书推送"""
    from action_executor import FeishuPush
    
    push = FeishuPush(webhook_url="https://open.feishu.cn/mock/webhook")
    
    work_order = {
        "id": "WO-20260601-003",
        "alert_level": "serious",
        "violation_type": "插瓶干扰"
    }
    
    # Mock requests.post
    with patch('action_executor.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"StatusCode": 0, "Status": "ok"}
        mock_post.return_value = mock_response
        
        result = push.execute(work_order)
        
        assert result.success is True
        assert result.channel == "feishu"
        assert mock_post.called


def test_feishu_push_execute_failure():
    """测试飞书推送失败"""
    from action_executor import FeishuPush
    
    push = FeishuPush(webhook_url="https://open.feishu.cn/mock/webhook")
    
    work_order = {"id": "WO-FAIL"}
    
    with patch('action_executor.requests.post') as mock_post:
        mock_post.side_effect = Exception("Network error")
        
        result = push.execute(work_order)
        
        assert result.success is False
        assert "Network error" in result.error
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_action_executor.py::test_feishu_push_execute -v
```

Expected: FAIL - "FeishuPush not found"

- [ ] **Step 3: 实现 FeishuPush 类**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py (追加)
import requests


class FeishuPush(PushChannel):
    """飞书推送渠道"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url
    
    def execute(self, work_order: Dict[str, Any]) -> ExecutionResult:
        """执行飞书推送"""
        if not self.webhook_url:
            return ExecutionResult(
                success=False,
                channel=self.get_channel_name(),
                message="飞书 Webhook URL 未配置",
                error="WEBHOOK_URL_NOT_CONFIGURED"
            )
        
        try:
            # 构建飞书消息
            alert_level = work_order.get("alert_level", "unknown")
            violation_type = work_order.get("violation_type", "unknown")
            work_order_id = work_order.get("id", "")
            
            # 颜色映射
            color_map = {
                "general": "blue",
                "moderate": "yellow",
                "serious": "red"
            }
            
            message = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"🚨 废水监测预警 - {violation_type}"
                        },
                        "template": color_map.get(alert_level, "blue")
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "fields": [
                                {
                                    "is_short": True,
                                    "text": {
                                        "tag": "lark_md",
                                        "content": f"**预警级别**\\n{alert_level}"
                                    }
                                },
                                {
                                    "is_short": True,
                                    "text": {
                                        "tag": "lark_md",
                                        "content": f"**工单编号**\\n{work_order_id}"
                                    }
                                }
                            ]
                        },
                        {
                            "tag": "action",
                            "actions": [
                                {
                                    "tag": "button",
                                    "text": {
                                        "tag": "plain_text",
                                        "content": "查看详情"
                                    },
                                    "type": "default",
                                    "url": f"https://your-platform.com/work-orders/{work_order_id}"
                                }
                            ]
                        }
                    ]
                }
            }
            
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Feishu message sent successfully for {work_order_id}")
                return ExecutionResult(
                    success=True,
                    channel=self.get_channel_name(),
                    message="飞书消息发送成功",
                    data=response.json()
                )
            else:
                logger.warning(f"Feishu API returned status {response.status_code}")
                return ExecutionResult(
                    success=False,
                    channel=self.get_channel_name(),
                    message=f"飞书API返回错误状态: {response.status_code}",
                    error=f"HTTP_{response.status_code}"
                )
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Feishu push failed: {e}")
            return ExecutionResult(
                success=False,
                channel=self.get_channel_name(),
                message="飞书推送失败",
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error in Feishu push: {e}")
            return ExecutionResult(
                success=False,
                channel=self.get_channel_name(),
                message="飞书推送异常",
                error=str(e)
            )
    
    def get_channel_name(self) -> str:
        return "feishu"
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_action_executor.py::test_feishu_push_execute -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py tests/subagents/test_action_executor.py
git commit -m "feat: implement FeishuPush channel"
```

---

### Task 1.4: 实现 RegulatoryPlatformPush 推送渠道

**Files:**
- Modify: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py`

- [ ] **Step 1: 编写测试 - RegulatoryPlatformPush**

```python
# tests/subagents/test_action_executor.py (追加)
def test_regulatory_platform_push_execute():
    """测试监管平台推送"""
    from action_executor import RegulatoryPlatformPush
    
    push = RegulatoryPlatformPush(
        api_url="https://api.platform.mock/v1/alerts",
        api_key="test-key"
    )
    
    work_order = {
        "id": "WO-20260601-004",
        "alert_level": "serious",
        "violation_type": "稀释排放"
    }
    
    with patch('action_executor.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"status": "success", "alert_id": "ALT-12345"}
        mock_post.return_value = mock_response
        
        result = push.execute(work_order)
        
        assert result.success is True
        assert result.channel == "platform"
        assert result.data["alert_id"] == "ALT-12345"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_action_executor.py::test_regulatory_platform_push_execute -v
```

Expected: FAIL - "RegulatoryPlatformPush not found"

- [ ] **Step 3: 实现 RegulatoryPlatformPush 类**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py (追加)
class RegulatoryPlatformPush(PushChannel):
    """监管平台推送渠道"""
    
    def __init__(self, api_url: str = None, api_key: str = None):
        self.api_url = api_url
        self.api_key = api_key
    
    def execute(self, work_order: Dict[str, Any]) -> ExecutionResult:
        """执行监管平台推送"""
        if not self.api_url:
            return ExecutionResult(
                success=False,
                channel=self.get_channel_name(),
                message="监管平台 API URL 未配置",
                error="API_URL_NOT_CONFIGURED"
            )
        
        if not self.api_key:
            return ExecutionResult(
                success=False,
                channel=self.get_channel_name(),
                message="监管平台 API Key 未配置",
                error="API_KEY_NOT_CONFIGURED"
            )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                json=work_order,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Regulatory platform push successful for {work_order.get('id')}")
                return ExecutionResult(
                    success=True,
                    channel=self.get_channel_name(),
                    message="监管平台推送成功",
                    data=response.json()
                )
            elif response.status_code == 401:
                return ExecutionResult(
                    success=False,
                    channel=self.get_channel_name(),
                    message="API 认证失败",
                    error="UNAUTHORIZED"
                )
            else:
                logger.warning(f"Regulatory platform returned status {response.status_code}")
                return ExecutionResult(
                    success=False,
                    channel=self.get_channel_name(),
                    message=f"监管平台返回错误: {response.status_code}",
                    error=f"HTTP_{response.status_code}"
                )
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Regulatory platform push failed: {e}")
            return ExecutionResult(
                success=False,
                channel=self.get_channel_name(),
                message="监管平台推送失败",
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error in regulatory platform push: {e}")
            return ExecutionResult(
                success=False,
                channel=self.get_channel_name(),
                message="监管平台推送异常",
                error=str(e)
            )
    
    def get_channel_name(self) -> str:
        return "platform"
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_action_executor.py::test_regulatory_platform_push_execute -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py tests/subagents/test_action_executor.py
git commit -m "feat: implement RegulatoryPlatformPush channel"
```

---

### Task 1.5: 实现 ActionExecutor 执行器

**Files:**
- Modify: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py`

- [ ] **Step 1: 编写测试 - ActionExecutor**

```python
# tests/subagents/test_action_executor.py (追加)
def test_action_executor_execute_single_channel():
    """测试单渠道执行"""
    from action_executor import ActionExecutor
    
    executor = ActionExecutor()
    
    work_order = {"id": "WO-TEST-001", "alert_level": "general"}
    
    result = executor.execute(work_order, selected_channels=["archive"])
    
    assert "archive" in result
    assert result["archive"].success is True


def test_action_executor_execute_multiple_channels():
    """测试多渠道并行执行"""
    from action_executor import ActionExecutor
    
    executor = ActionExecutor()
    
    work_order = {"id": "WO-TEST-002", "alert_level": "serious"}
    
    result = executor.execute(work_order, selected_channels=["archive", "feishu"])
    
    assert len(result) == 2
    assert result["archive"].success is True
    # feishu 会因为未配置 webhook 而失败，但不会影响 archive


def test_action_executor_invalid_channel():
    """测试无效渠道"""
    from action_executor import ActionExecutor
    
    executor = ActionExecutor()
    
    work_order = {"id": "WO-TEST-003"}
    
    result = executor.execute(work_order, selected_channels=["invalid_channel"])
    
    assert len(result) == 1
    assert "invalid_channel" in result
    assert result["invalid_channel"].success is False
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_action_executor.py::test_action_executor_execute_single_channel -v
```

Expected: FAIL - "ActionExecutor not found"

- [ ] **Step 3: 实现 ActionExecutor 类**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py (追加)
class ActionExecutor:
    """行动执行器 - 协调多个推送渠道"""
    
    def __init__(self, config_path: str = "shared/configs/disposition_config.yaml"):
        """初始化执行器
        
        Args:
            config_path: 配置文件路径
        """
        self.channels = {}
        self._load_channels(config_path)
    
    def _load_channels(self, config_path: str):
        """从配置文件加载渠道"""
        try:
            import yaml
            from pathlib import Path
            
            config_file = Path(config_path)
            if not config_file.exists():
                # 使用默认配置
                logger.warning(f"Config file not found: {config_path}, using defaults")
                self._init_default_channels()
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            action_config = config.get("action_executor", {})
            
            # 初始化本地归档
            if action_config.get("archive", {}).get("enabled", True):
                archive_config = action_config["archive"]
                output_dir = archive_config.get("output_dir", "/shared/outputs/work_orders/")
                self.channels["archive"] = LocalArchive(output_dir=output_dir)
            
            # 初始化飞书推送
            if action_config.get("feishu", {}).get("enabled", False):
                feishu_config = action_config["feishu"]
                webhook_url = feishu_config.get("webhook_url")
                if webhook_url:
                    self.channels["feishu"] = FeishuPush(webhook_url=webhook_url)
            
            # 初始化监管平台推送
            if action_config.get("platform", {}).get("enabled", False):
                platform_config = action_config["platform"]
                api_url = platform_config.get("api_url")
                api_key = platform_config.get("api_key")
                if api_url and api_key:
                    self.channels["platform"] = RegulatoryPlatformPush(
                        api_url=api_url,
                        api_key=api_key
                    )
                    
        except Exception as e:
            logger.error(f"Failed to load channels from config: {e}, using defaults")
            self._init_default_channels()
    
    def _init_default_channels(self):
        """初始化默认渠道（仅本地归档）"""
        self.channels["archive"] = LocalArchive()
    
    def execute(
        self,
        work_order: Dict[str, Any],
        selected_channels: List[str] = None
    ) -> Dict[str, ExecutionResult]:
        """执行多渠道推送
        
        Args:
            work_order: 工单数据
            selected_channels: 选择的推送渠道列表，None 表示使用所有可用渠道
            
        Returns:
            Dict[str, ExecutionResult]: 各渠道的执行结果
        """
        if selected_channels is None:
            selected_channels = list(self.channels.keys())
        
        results = {}
        
        for channel_name in selected_channels:
            if channel_name not in self.channels:
                results[channel_name] = ExecutionResult(
                    success=False,
                    channel=channel_name,
                    message=f"渠道 '{channel_name}' 不存在",
                    error="CHANNEL_NOT_FOUND"
                )
                logger.warning(f"Channel not found: {channel_name}")
                continue
            
            channel = self.channels[channel_name]
            try:
                result = channel.execute(work_order)
                results[channel_name] = result
                
                # 记录执行结果
                if result.success:
                    logger.info(f"Channel {channel_name} succeeded: {result.message}")
                else:
                    logger.warning(f"Channel {channel_name} failed: {result.error}")
                    
            except Exception as e:
                logger.error(f"Unexpected error executing channel {channel_name}: {e}")
                results[channel_name] = ExecutionResult(
                    success=False,
                    channel=channel_name,
                    message=f"渠道执行异常",
                    error=str(e)
                )
        
        return results
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_action_executor.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py tests/subagents/test_action_executor.py
git commit -m "feat: implement ActionExecutor coordinator"
```

---

## 阶段2: report_generator.py 实现

### Task 2.1: 创建报告数据结构

**Files:**
- Create: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py`

- [ ] **Step 1: 编写测试 - 报告数据类**

```python
# tests/subagents/test_report_generator.py
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "subagents" / "disposition-execution-agent" / "skills" / "disposition-execution-core" / "scripts"))

from report_generator import AlertReport, SummaryReport, TrendReport


def test_alert_report_creation():
    """测试 AlertReport 创建"""
    report = AlertReport(
        report_id="RPT-001",
        generated_at="2026-06-01T10:00:00",
        alert_level="serious",
        violation_type="稀释排放",
        confidence=0.92,
        data_traceback={},
        inspection_points=[],
        legal_references=[],
        recommended_actions=[]
    )
    
    assert report.report_id == "RPT-001"
    assert report.alert_level == "serious"
    assert report.confidence == 0.92


def test_summary_report_creation():
    """测试 SummaryReport 创建"""
    report = SummaryReport(
        report_id="SUM-001",
        generated_at="2026-06-01T10:00:00",
        time_range=("2026-06-01 00:00:00", "2026-06-01 23:59:59"),
        total_alerts=10,
        by_level={"general": 5, "moderate": 3, "serious": 2},
        by_type={"插瓶干扰": 3, "稀释排放": 4, "人工拟合": 3},
        top_enterprises=[]
    )
    
    assert report.total_alerts == 10
    assert report.by_level["serious"] == 2


def test_trend_report_creation():
    """测试 TrendReport 创建"""
    report = TrendReport(
        report_id="TREND-001",
        generated_at="2026-06-01T10:00:00",
        time_range=("2026-06-01 00:00:00", "2026-06-01 23:59:59"),
        indicators=["COD", "TN", "TP"],
        trend_data={},
        analysis="无明显趋势",
        anomalies=[]
    )
    
    assert len(report.indicators) == 3
    assert report.analysis == "无明显趋势"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_report_generator.py::test_alert_report_creation -v
```

Expected: FAIL - "ModuleNotFoundError: No module named 'report_generator'"

- [ ] **Step 3: 实现报告数据类**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py
"""
报告生成模块 - 生成预警、汇总和趋势报告
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class AlertReport:
    """预警报告"""
    report_id: str
    generated_at: str
    alert_level: str
    violation_type: str
    confidence: float
    
    # 报告内容
    data_traceback: Dict[str, Any]
    inspection_points: List[Dict[str, Any]]
    legal_references: List[str]
    recommended_actions: List[str]
    
    # 趋势图表数据（可选）
    trend_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "alert_level": self.alert_level,
            "violation_type": self.violation_type,
            "confidence": self.confidence,
            "data_traceback": self.data_traceback,
            "inspection_points": self.inspection_points,
            "legal_references": self.legal_references,
            "recommended_actions": self.recommended_actions,
            "trend_data": self.trend_data
        }
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        md = f"""# 预警报告

## 基本信息
- 报告编号: {self.report_id}
- 生成时间: {self.generated_at}
- 预警级别: {self.alert_level}
- 违规类型: {self.violation_type}
- 置信度: {self.confidence:.1%}

## 数据溯源
{self._format_dict(self.data_traceback)}

## 现场核查要点
{self._format_list(self.inspection_points)}

## 法规条款
{self._format_list(self.legal_references)}

## 处置建议
{self._format_list(self.recommended_actions)}
"""
        return md
    
    @staticmethod
    def _format_dict(d: Dict) -> str:
        if not d:
            return "无"
        return "\\n".join([f"- {k}: {v}" for k, v in d.items()])
    
    @staticmethod
    def _format_list(lst: List) -> str:
        if not lst:
            return "无"
        return "\\n".join([f"- {item}" for item in lst])


@dataclass
class SummaryReport:
    """汇总报告"""
    report_id: str
    generated_at: str
    time_range: Tuple[str, str]
    total_alerts: int
    by_level: Dict[str, int]
    by_type: Dict[str, int]
    top_enterprises: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "time_range": self.time_range,
            "total_alerts": self.total_alerts,
            "by_level": self.by_level,
            "by_type": self.by_type,
            "top_enterprises": self.top_enterprises
        }
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        md = f"""# 汇总报告

## 基本信息
- 报告编号: {self.report_id}
- 生成时间: {self.generated_at}
- 统计时间: {self.time_range[0]} 至 {self.time_range[1]}
- 总预警数: {self.total_alerts}

## 按级别统计
{self._format_dict(self.by_level)}

## 按类型统计
{self._format_dict(self.by_type)}

## 重点企业
{self._format_enterprises()}
"""
        return md
    
    @staticmethod
    def _format_dict(d: Dict) -> str:
        if not d:
            return "无"
        return "\\n".join([f"- {k}: {v}" for k, v in d.items()])
    
    def _format_enterprises(self) -> str:
        if not self.top_enterprises:
            return "无"
        lines = []
        for i, ent in enumerate(self.top_enterprises, 1):
            name = ent.get("name", "未知")
            count = ent.get("alert_count", 0)
            lines.append(f"{i}. {name}: {count} 次")
        return "\\n".join(lines)


@dataclass
class TrendReport:
    """趋势分析报告"""
    report_id: str
    generated_at: str
    time_range: Tuple[str, str]
    indicators: List[str]
    trend_data: Dict[str, List[Dict[str, Any]]]
    analysis: str
    anomalies: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "time_range": self.time_range,
            "indicators": self.indicators,
            "trend_data": self.trend_data,
            "analysis": self.analysis,
            "anomalies": self.anomalies
        }
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        indicators_str = ", ".join(self.indicators)
        md = f"""# 趋势分析报告

## 基本信息
- 报告编号: {self.report_id}
- 生成时间: {self.generated_at}
- 分析时间: {self.time_range[0]} 至 {self.time_range[1]}
- 分析指标: {indicators_str}

## 趋势分析
{self.analysis}

## 异常事件
{self._format_anomalies()}
"""
        return md
    
    def _format_anomalies(self) -> str:
        if not self.anomalies:
            return "无异常事件"
        lines = []
        for i, anom in enumerate(self.anomalies, 1):
            time_str = anom.get("time", "未知时间")
            desc = anom.get("description", "无描述")
            lines.append(f"{i}. {time_str}: {desc}")
        return "\\n".join(lines)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_report_generator.py::test_alert_report_creation -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py tests/subagents/test_report_generator.py
git commit -m "feat: add report data classes"
```

---

### Task 2.2: 实现 ReportGenerator - AlertReport

**Files:**
- Modify: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py`

- [ ] **Step 1: 编写测试 - ReportGenerator.generate_alert_report**

```python
# tests/subagents/test_report_generator.py (追加)
def test_generate_alert_report():
    """测试生成预警报告"""
    from report_generator import ReportGenerator
    
    generator = ReportGenerator()
    
    work_order = {
        "id": "WO-20260601-001",
        "alert_level": "serious",
        "violation_type": "稀释排放",
        "confidence": 0.92,
        "data_traceback": {
            "time_range": {"start": "2026-06-01 02:00", "end": "2026-06-01 04:00"},
            "affected_indicators": ["COD", "TN", "TP"]
        },
        "inspection_points": [
            {"location": "废水排放口", "action": "采集出水样品"}
        ],
        "legal_references": ["《水污染防治法》第XX条"],
        "recommended_actions": ["立即启动执法程序"]
    }
    
    context = {
        "enterprise_name": "测试企业"
    }
    
    report = generator.generate_alert_report(work_order, context)
    
    assert isinstance(report, AlertReport)
    assert report.report_id.startswith("ALERT-")
    assert report.alert_level == "serious"
    assert report.violation_type == "稀释排放"
    assert len(report.legal_references) > 0
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_report_generator.py::test_generate_alert_report -v
```

Expected: FAIL - "ReportGenerator not found"

- [ ] **Step 3: 实现 ReportGenerator.generate_alert_report**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py (追加)
class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = "/shared/outputs/reports/"):
        self.output_dir = output_dir
    
    def generate_alert_report(
        self,
        work_order: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> AlertReport:
        """生成单个预警的详细报告
        
        Args:
            work_order: 工单数据
            context: 上下文信息（历史数据、趋势等）
            
        Returns:
            AlertReport: 预警报告
        """
        if context is None:
            context = {}
        
        # 生成报告ID
        report_id = f"ALERT-{work_order.get('id', 'unknown')}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 从工单中提取数据
        data_traceback = work_order.get("data_traceback", {})
        inspection_points = work_order.get("inspection_points", [])
        legal_references = work_order.get("legal_references", [])
        recommended_actions = work_order.get("recommended_actions", [])
        
        # 如果工单中没有趋势数据，可以从 context 中获取
        trend_data = context.get("trend_data")
        
        report = AlertReport(
            report_id=report_id,
            generated_at=datetime.now().isoformat(),
            alert_level=work_order.get("alert_level", "unknown"),
            violation_type=work_order.get("violation_type", "unknown"),
            confidence=work_order.get("confidence", 0.0),
            data_traceback=data_traceback,
            inspection_points=inspection_points,
            legal_references=legal_references,
            recommended_actions=recommended_actions,
            trend_data=trend_data
        )
        
        logger.info(f"Generated alert report: {report_id}")
        return report
    
    def save_report(self, report: Union[AlertReport, SummaryReport, TrendReport]) -> str:
        """保存报告到文件
        
        Args:
            report: 报告对象
            
        Returns:
            str: 文件路径
        """
        try:
            from pathlib import Path
            
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 确定文件名
            report_id = report.report_id.replace("/", "-")
            filename = f"{report_id}.json"
            file_path = output_path / filename
            
            # 保存 JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                if hasattr(report, 'to_dict'):
                    json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
                else:
                    json.dump(report.__dict__, f, ensure_ascii=False, indent=2)
            
            # 同时保存 Markdown
            md_filename = f"{report_id}.md"
            md_file_path = output_path / md_filename
            with open(md_file_path, 'w', encoding='utf-8') as f:
                if hasattr(report, 'to_markdown'):
                    f.write(report.to_markdown())
            
            logger.info(f"Report saved to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            raise
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_report_generator.py::test_generate_alert_report -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py tests/subagents/test_report_generator.py
git commit -m "feat: implement ReportGenerator.generate_alert_report"
```

---

### Task 2.3: 实现 ReportGenerator - SummaryReport

**Files:**
- Modify: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py`

- [ ] **Step 1: 编写测试 - generate_summary_report**

```python
# tests/subagents/test_report_generator.py (追加)
def test_generate_summary_report():
    """测试生成汇总报告"""
    from report_generator import ReportGenerator
    
    generator = ReportGenerator()
    
    work_orders = [
        {"alert_level": "general", "violation_type": "插瓶干扰", "confidence": 0.5},
        {"alert_level": "moderate", "violation_type": "稀释排放", "confidence": 0.7},
        {"alert_level": "serious", "violation_type": "人工拟合", "confidence": 0.9},
        {"alert_level": "serious", "violation_type": "稀释排放", "confidence": 0.85}
    ]
    
    time_range = ("2026-06-01 00:00:00", "2026-06-01 23:59:59")
    
    report = generator.generate_summary_report(work_orders, time_range)
    
    assert isinstance(report, SummaryReport)
    assert report.total_alerts == 4
    assert report.by_level["general"] == 1
    assert report.by_level["serious"] == 2
    assert report.by_type["稀释排放"] == 2
    assert report.report_id.startswith("SUMMARY-")
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_report_generator.py::test_generate_summary_report -v
```

Expected: FAIL - "generate_summary_report not found"

- [ ] **Step 3: 实现 generate_summary_report**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py (追加)
    def generate_summary_report(
        self,
        work_orders: List[Dict[str, Any]],
        time_range: Tuple[str, str]
    ) -> SummaryReport:
        """生成汇总报告
        
        Args:
            work_orders: 工单列表
            time_range: 时间范围
            
        Returns:
            SummaryReport: 汇总报告
        """
        # 统计按级别的数量
        by_level = {"general": 0, "moderate": 0, "serious": 0}
        by_type = {}
        
        for wo in work_orders:
            level = wo.get("alert_level", "unknown")
            if level in by_level:
                by_level[level] += 1
            
            vtype = wo.get("violation_type", "unknown")
            by_type[vtype] = by_type.get(vtype, 0) + 1
        
        # 统计重点企业（如果有企业信息）
        top_enterprises = []
        # TODO: 根据企业分组统计
        
        report = SummaryReport(
            report_id=f"SUMMARY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            generated_at=datetime.now().isoformat(),
            time_range=time_range,
            total_alerts=len(work_orders),
            by_level=by_level,
            by_type=by_type,
            top_enterprises=top_enterprises
        )
        
        logger.info(f"Generated summary report: {report.report_id}")
        return report
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_report_generator.py::test_generate_summary_report -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py tests/subagents/test_report_generator.py
git commit -m "feat: implement ReportGenerator.generate_summary_report"
```

---

### Task 2.4: 实现 ReportGenerator - TrendReport

**Files:**
- Modify: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py`

- [ ] **Step 1: 编写测试 - generate_trend_report**

```python
# tests/subagents/test_report_generator.py (追加)
def test_generate_trend_report():
    """测试生成趋势报告"""
    from report_generator import ReportGenerator
    
    generator = ReportGenerator()
    
    # 模拟历史数据
    historical_data = [
        {"监测时间": "2026-06-01 00:00", "COD": 45, "TN": 15, "TP": 3},
        {"监测时间": "2026-06-01 06:00", "COD": 50, "TN": 18, "TP": 4},
        {"监测时间": "2026-06-01 12:00", "COD": 48, "TN": 16, "TP": 3.5},
        {"监测时间": "2026-06-01 18:00", "COD": 52, "TN": 20, "TP": 5}
    ]
    
    indicators = ["COD", "TN"]
    time_range = ("2026-06-01 00:00:00", "2026-06-01 23:59:59")
    
    report = generator.generate_trend_report(historical_data, indicators, time_range)
    
    assert isinstance(report, TrendReport)
    assert report.report_id.startswith("TREND-")
    assert len(report.indicators) == 2
    assert "COD" in report.trend_data
    assert "analysis" != ""
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_report_generator.py::test_generate_trend_report -v
```

Expected: FAIL - "generate_trend_report not found"

- [ ] **Step 3: 实现 generate_trend_report**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py (追加)
    def generate_trend_report(
        self,
        historical_data: List[Dict[str, Any]],
        indicators: List[str],
        time_range: Tuple[str, str]
    ) -> TrendReport:
        """生成趋势分析报告
        
        Args:
            historical_data: 历史数据列表
            indicators: 需要分析的指标列表
            time_range: 时间范围
            
        Returns:
            TrendReport: 趋势报告
        """
        # 提取趋势数据
        trend_data = {}
        anomalies = []
        
        for indicator in indicators:
            values = []
            for record in historical_data:
                value = record.get(indicator)
                if value is not None:
                    values.append({
                        "time": record.get("监测时间", ""),
                        "value": value
                    })
            
            trend_data[indicator] = values
            
            # 简单异常检测
            if len(values) > 1:
                numeric_values = [v["value"] for v in values if isinstance(v["value"], (int, float))]
                if numeric_values:
                    avg = sum(numeric_values) / len(numeric_values)
                    std = (sum((x - avg) ** 2 for x in numeric_values) / len(numeric_values)) ** 0.5
                    
                    for v in values:
                        val = v["value"]
                        if isinstance(val, (int, float)) and abs(val - avg) > 2 * std:
                            anomalies.append({
                                "time": v["time"],
                                "indicator": indicator,
                                "value": val,
                                "description": f"{indicator} 异常: {val} (均值: {avg:.2f}, 标准差: {std:.2f})"
                            })
        
        # 生成分析文本
        analysis_lines = []
        for indicator in indicators:
            if indicator in trend_data and len(trend_data[indicator]) > 0:
                values_count = len(trend_data[indicator])
                analysis_lines.append(f"- {indicator}: 共 {values_count} 个数据点")
                
                # 简单趋势判断
                if values_count >= 2:
                    first_val = trend_data[indicator][0].get("value")
                    last_val = trend_data[indicator][-1].get("value")
                    if isinstance(first_val, (int, float)) and isinstance(last_val, (int, float)):
                        if last_val > first_val * 1.2:
                            analysis_lines.append(f"  趋势: 上升")
                        elif last_val < first_val * 0.8:
                            analysis_lines.append(f"  趋势: 下降")
                        else:
                            analysis_lines.append(f"  趋势: 平稳")
        
        analysis = "\\n".join(analysis_lines) if analysis_lines else "无趋势数据"
        
        report = TrendReport(
            report_id=f"TREND-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            generated_at=datetime.now().isoformat(),
            time_range=time_range,
            indicators=indicators,
            trend_data=trend_data,
            analysis=analysis,
            anomalies=anomalies
        )
        
        logger.info(f"Generated trend report: {report.report_id}")
        return report
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_report_generator.py::test_generate_trend_report -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py tests/subagents/test_report_generator.py
git commit -m "feat: implement ReportGenerator.generate_trend_report"
```

---

## 阶段3: 集成和配置

### Task 3.1: 创建配置文件

**Files:**
- Create: `shared/configs/disposition_config.yaml`

- [ ] **Step 1: 创建配置文件**

```yaml
# shared/configs/disposition_config.yaml
# 研判预警与处置执行配置

action_executor:
  # 飞书推送配置
  feishu:
    webhook_url: "${FEISHU_WEBHOOK_URL:}"
    enabled: false  # 默认关闭，需要配置 Webhook 后启用
  
  # 监管平台推送配置
  platform:
    api_url: "${PLATFORM_API_URL:}"
    api_key: "${PLATFORM_API_KEY:}"
    enabled: false  # 默认关闭，需要配置 API 后启用
  
  # 本地归档配置
  archive:
    output_dir: "/shared/outputs/work_orders/"
    enabled: true  # 默认启用

report_generator:
  # 报告输出目录
  output_dir: "/shared/outputs/reports/"
  
  # 支持的报告格式
  formats:
    - json
    - markdown
  
  # 是否包含趋势图表数据
  include_trend_charts: true
```

- [ ] **Step 2: 验证 YAML 语法**

```bash
python -c "import yaml; yaml.safe_load(open('shared/configs/disposition_config.yaml'))"
echo "YAML syntax valid"
```

Expected: "YAML syntax valid"

- [ ] **Step 3: 提交**

```bash
git add shared/configs/disposition_config.yaml
git commit -m "config: add disposition execution configuration"
```

---

### Task 3.2: 更新 __init__.py 导出

**Files:**
- Modify: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/__init__.py`

- [ ] **Step 1: 更新 __init__.py**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/__init__.py
"""研判预警与处置执行脚本模块"""
from .alert_classifier import AlertClassifier, AlertLevel, ActionRequired
from .work_order_generator import WorkOrderGenerator
from .action_executor import (
    ActionExecutor, 
    ExecutionResult, 
    PushChannel,
    LocalArchive,
    FeishuPush,
    RegulatoryPlatformPush
)
from .report_generator import (
    ReportGenerator,
    AlertReport,
    SummaryReport,
    TrendReport
)

__all__ = [
    'AlertClassifier', 'AlertLevel', 'ActionRequired',
    'WorkOrderGenerator',
    'ActionExecutor', 'ExecutionResult', 'PushChannel',
    'LocalArchive', 'FeishuPush', 'RegulatoryPlatformPush',
    'ReportGenerator', 'AlertReport', 'SummaryReport', 'TrendReport'
]
```

- [ ] **Step 2: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/__init__.py
git commit -m "refactor: update exports for action_executor and report_generator"
```

---

### Task 3.3: 更新 SKILL.md

**Files:**
- Modify: `subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md`

- [ ] **Step 1: 更新 SKILL.md**

```markdown
# 研判预警与处置执行核心技能包

## 技能描述
本技能包提供融合共识、预警分级、工单生成、行动执行和报告生成能力，完成从违规识别到处置执行的闭环。

## 核心脚本

### 1. alert_classifier.py (AlertClassifier)
**功能**: 三级预警分级
- classify_alert(): 对异常和违规结果进行预警分级
- 支持一般/较重/严重三级预警

### 2. work_order_generator.py (WorkOrderGenerator)
**功能**: 处置工单生成
- generate_work_order(): 生成标准化处置工单
- 工单包含：数据溯源、核查要点、法规条款、历史参考

### 3. action_executor.py (ActionExecutor)
**功能**: 行动执行
- execute(): 并行执行多渠道推送
- 支持渠道：RegulatoryPlatformPush, FeishuPush, LocalArchive
- 接口抽象：PushChannel 基类

### 4. report_generator.py (ReportGenerator)
**功能**: 报告生成
- generate_alert_report(): 生成预警报告
- generate_summary_report(): 生成汇总报告
- generate_trend_report(): 生成趋势分析报告
- 支持 JSON 和 Markdown 输出格式

## LLM决策点
1. 融合策略: 根据场景动态调整定量定性权重
2. 分级判定: 综合判断预警级别
3. 工单内容: 根据违规类型生成个性化工单

## 输出格式
标准化预警信息、处置工单和报告
```

- [ ] **Step 2: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md
git commit -m "docs: update SKILL.md for action_executor and report_generator"
```

---

## 验收标准

完成所有任务后，系统应该具备以下能力：

1. ✅ ActionExecutor 可以执行多渠道推送
2. ✅ LocalArchive 可以将工单保存到本地文件
3. ✅ FeishuPush 可以发送飞书消息（需要配置）
4. ✅ RegulatoryPlatformPush 可以调用监管平台 API（需要配置）
5. ✅ ReportGenerator 可以生成预警报告
6. ✅ ReportGenerator 可以生成汇总报告
7. ✅ ReportGenerator 可以生成趋势分析报告
8. ✅ 所有报告支持 JSON 和 Markdown 格式
9. ✅ 推送失败不影响其他渠道执行
10. ✅ 配置文件支持渠道开关

---

## 总计任务数

- 阶段1（action_executor）: 5个任务
- 阶段2（report_generator）: 4个任务
- 阶段3（集成）: 3个任务

**总计: 12个任务**

---

**实施优先级**: 按阶段顺序执行。

**回滚计划**: 每个阶段提交后打 tag，便于回滚到指定阶段。