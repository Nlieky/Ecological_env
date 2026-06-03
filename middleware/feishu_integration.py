#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书集成模块
功能：发送告警消息到飞书机器人
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FeishuConfig:
    """飞书配置"""
    webhook_url: str
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    enabled: bool = True


class FeishuIntegration:
    """
    飞书集成类

    支持功能：
    1. 发送文本消息
    2. 发送富文本消息
    3. 发送卡片消息
    4. 发送告警卡片
    """

    # 颜色定义
    COLOR_RED = "FF4D4F"      # 严重
    COLOR_ORANGE = "FF7A45"   # 警告
    COLOR_YELLOW = "FFC53D"   # 提醒
    COLOR_GREEN = "52C41A"    # 正常
    COLOR_BLUE = "1890FF"     # 信息
    COLOR_GREY = "8C8C8C"     # 灰色

    def __init__(self, config: FeishuConfig):
        """初始化飞书集成"""
        self.config = config
        self.session = requests.Session()
        logger.info(f"[FEISHU] 飞书集成已初始化")

    def _send_request(self, data: Dict[str, Any]) -> bool:
        """
        发送请求到飞书

        Args:
            data: 请求数据

        Returns:
            是否发送成功
        """
        if not self.config.enabled:
            logger.debug("[FEISHU] 飞书通知已禁用，跳过发送")
            return False

        try:
            response = self.session.post(
                self.config.webhook_url,
                json=data,
                timeout=10
            )

            result = response.json()

            if result.get('StatusCode') == 0 or result.get('code') == 0:
                logger.debug("[FEISHU] 消息发送成功")
                return True
            else:
                logger.error(f"[FEISHU] 消息发送失败: {result}")
                return False

        except Exception as e:
            logger.error(f"[FEISHU] 发送请求失败: {e}")
            return False

    def send_text(self, content: str) -> bool:
        """
        发送文本消息

        Args:
            content: 文本内容

        Returns:
            是否发送成功
        """
        data = {
            "msg_type": "text",
            "content": {"text": content}
        }
        return self._send_request(data)

    def send_post(self, title: str, content: List[Dict[str, Any]]) -> bool:
        """
        发送富文本消息

        Args:
            title: 标题
            content: 内容列表，格式: [{"tag": "text", "text": "内容"}, ...]

        Returns:
            是否发送成功
        """
        data = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": [content]
                    }
                }
            }
        }
        return self._send_request(data)

    def send_card(self, card_content: Dict[str, Any]) -> bool:
        """
        发送卡片消息

        Args:
            card_content: 卡片内容

        Returns:
            是否发送成功
        """
        data = {
            "msg_type": "interactive",
            "card": card_content
        }
        return self._send_request(data)

    def send_anomaly_alert(
        self,
        indicator: str,
        value: float,
        threshold: float,
        severity: str = "warning",
        timestamp: Optional[str] = None
    ) -> bool:
        """
        发送异常告警卡片

        Args:
            indicator: 指标名称
            value: 当前值
            threshold: 阈值
            severity: 严重程度 (critical, warning, info)
            timestamp: 时间戳

        Returns:
            是否发送成功
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 根据严重程度选择颜色
        color_map = {
            "critical": self.COLOR_RED,
            "warning": self.COLOR_ORANGE,
            "info": self.COLOR_BLUE
        }
        color = color_map.get(severity, self.COLOR_BLUE)

        # 严重程度中文
        severity_map = {
            "critical": "严重",
            "warning": "警告",
            "info": "信息"
        }
        severity_cn = severity_map.get(severity, "未知")

        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "content": f"🚨 废水监测异常告警",
                    "tag": "plain_text"
                },
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**指标名称:**\n{indicator}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**严重程度:**\n{severity_cn}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**当前值:**\n{value}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**阈值:**\n{threshold}"
                            }
                        },
                        {
                            "is_short": False,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**发生时间:**\n{timestamp}"
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
                                "content": "查看详情",
                                "tag": "plain_text"
                            },
                            "type": "default",
                            "url": f"http://localhost:3000/d/wastewater-monitoring?var-indicator={indicator}"
                        }
                    ]
                }
            ]
        }

        return self.send_card(card)

    def send_violation_alert(
        self,
        regulation: str,
        description: str,
        severity: str = "warning",
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送违规告警卡片

        Args:
            regulation: 规则名称
            description: 违规描述
            severity: 严重程度
            details: 详细信息

        Returns:
            是否发送成功
        """
        color_map = {
            "critical": self.COLOR_RED,
            "warning": self.COLOR_ORANGE,
            "info": self.COLOR_BLUE
        }
        color = color_map.get(severity, self.COLOR_BLUE)

        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "content": f"⚠️ 环保规则违规告警",
                    "tag": "plain_text"
                },
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**规则名称:**\n{regulation}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**发生时间:**\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        }
                    ]
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**违规描述:**\n{description}"
                    }
                }
            ]
        }

        if details:
            detail_text = "\n".join([f"- {k}: {v}" for k, v in details.items()])
            card["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**详细信息:**\n{detail_text}"
                }
            })

        return self.send_card(card)

    def send_daily_report(
        self,
        total_records: int,
        anomaly_count: int,
        violation_count: int,
        quality_score: float
    ) -> bool:
        """
        发送每日报告卡片

        Args:
            total_records: 总记录数
            anomaly_count: 异常数量
            violation_count: 违规数量
            quality_score: 水质评分

        Returns:
            是否发送成功
        """
        # 根据评分确定颜色
        if quality_score >= 90:
            color = self.COLOR_GREEN
            status = "优秀"
        elif quality_score >= 75:
            color = self.COLOR_BLUE
            status = "良好"
        elif quality_score >= 60:
            color = self.COLOR_YELLOW
            status = "一般"
        else:
            color = self.COLOR_RED
            status = "较差"

        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "content": f"📊 废水监测每日报告",
                    "tag": "plain_text"
                },
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**日期:** {datetime.now().strftime('%Y-%m-%d')}"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**处理记录**\n{total_records:,}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**异常数量**\n{anomaly_count}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**违规数量**\n{violation_count}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**水质评分**\n{quality_score:.1f} ({status})"
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
                                "content": "查看仪表板",
                                "tag": "plain_text"
                            },
                            "type": "primary",
                            "url": "http://localhost:3000/d/wastewater-monitoring"
                        }
                    ]
                }
            ]
        }

        return self.send_card(card)


def create_feishu_from_env() -> Optional[FeishuIntegration]:
    """
    从环境变量创建飞书集成实例

    Returns:
        FeishuIntegration实例，如果配置不完整则返回None
    """
    webhook_url = os.getenv('FEISHU_WEBHOOK_URL')

    if not webhook_url:
        logger.warning("[FEISHU] 未配置FEISHU_WEBHOOK_URL，飞书通知将被禁用")
        return None

    config = FeishuConfig(
        webhook_url=webhook_url,
        app_id=os.getenv('FEISHU_APP_ID'),
        app_secret=os.getenv('FEISHU_APP_SECRET'),
        enabled=os.getenv('FEISHU_ENABLED', 'true').lower() == 'true'
    )

    return FeishuIntegration(config)


# 单例实例
_feishu_instance: Optional[FeishuIntegration] = None


def get_feishu() -> Optional[FeishuIntegration]:
    """
    获取飞书集成单例实例

    Returns:
        FeishuIntegration实例
    """
    global _feishu_instance

    if _feishu_instance is None:
        _feishu_instance = create_feishu_from_env()

    return _feishu_instance


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    # 测试配置（请替换为实际的webhook）
    test_config = FeishuConfig(
        webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
        enabled=False  # 设置为True启用实际发送
    )

    feishu = FeishuIntegration(test_config)

    # 测试文本消息
    feishu.send_text("这是一条测试消息")

    # 测试异常告警
    feishu.send_anomaly_alert(
        indicator="pH值",
        value=8.5,
        threshold=8.0,
        severity="warning"
    )

    # 测试每日报告
    feishu.send_daily_report(
        total_records=10000,
        anomaly_count=5,
        violation_count=1,
        quality_score=85.5
    )
