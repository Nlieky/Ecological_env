"""
日志数据库维护脚本
提供日志清理、统计等功能
"""
import sys
import os
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from backend.database.session import SessionLocal
from backend.models.logging import (
    APICallLog,
    MasterAgentDecisionLog,
    SubAgentExecutionLog,
    OperatorCallLog,
    LLMCallLog,
    SystemErrorLog
)


def get_log_stats():
    """获取日志统计信息"""
    db = SessionLocal()
    try:
        stats = {}

        stats['api_calls'] = db.query(APICallLog).count()
        stats['master_decisions'] = db.query(MasterAgentDecisionLog).count()
        stats['subagent_executions'] = db.query(SubAgentExecutionLog).count()
        stats['operator_calls'] = db.query(OperatorCallLog).count()
        stats['llm_calls'] = db.query(LLMCallLog).count()
        stats['system_errors'] = db.query(SystemErrorLog).count()

        print("=== Log Statistics ===")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        return stats
    finally:
        db.close()


def clean_old_logs(days: int = 30):
    """清理指定天数之前的日志"""
    db = SessionLocal()
    try:
        cutoff_time = datetime.now() - timedelta(days=days)

        models = [
            APICallLog,
            MasterAgentDecisionLog,
            SubAgentExecutionLog,
            OperatorCallLog,
            LLMCallLog
        ]

        total_deleted = 0
        for model in models:
            deleted = db.query(model).filter(model.timestamp < cutoff_time).delete()
            total_deleted += deleted
            print(f"  {model.__tablename__}: deleted {deleted} records")

        db.commit()
        print(f"[OK] Total deleted: {total_deleted} old logs")
    finally:
        db.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Log database maintenance")
    parser.add_argument('action', choices=['stats', 'clean'], help='Action type')
    parser.add_argument('--days', type=int, default=30, help='Delete logs older than N days')

    args = parser.parse_args()

    if args.action == 'stats':
        get_log_stats()
    elif args.action == 'clean':
        print(f"Cleaning logs older than {args.days} days:")
        clean_old_logs(args.days)


if __name__ == "__main__":
    main()
