from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool
import os

# 数据库文件路径
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
DB_PATH = os.path.join(DB_DIR, "ecological_logs.db")

# 确保 logs 目录存在
os.makedirs(DB_DIR, exist_ok=True)

# 数据库 URL
DATABASE_URL = f"sqlite:///{DB_PATH}"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # SQLite 单线程
    echo=False  # 生产环境设为 False
)

# 声明基类
Base = declarative_base()
