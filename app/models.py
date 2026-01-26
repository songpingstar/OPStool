from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class ScriptCategory(Base):
    __tablename__ = "script_category"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    order = Column(Integer, default=0)

    scripts = relationship("ScriptItem", back_populates="category")


class ScriptItem(Base):
    __tablename__ = "script_item"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("script_category.id"))
    title = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    script_type = Column(String(50), nullable=False)  # python/shell/powershell
    exec_command_template = Column(String(500), nullable=True)
    script_path = Column(String(500), nullable=True)
    enabled = Column(Boolean, default=True)
    is_dangerous = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    category = relationship("ScriptCategory", back_populates="scripts")
    versions = relationship(
        "ScriptVersion", back_populates="script", order_by="ScriptVersion.version"
    )
    exec_records = relationship(
        "ScriptExecRecord",
        back_populates="script",
        order_by="desc(ScriptExecRecord.start_time)",
    )


class ScriptVersion(Base):
    __tablename__ = "script_version"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("script_item.id"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    editor = Column(String(100), nullable=True)
    remark = Column(String(255), nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)

    script = relationship("ScriptItem", back_populates="versions")


class ScriptExecRecord(Base):
    __tablename__ = "script_exec_record"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("script_item.id"), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")  # running/success/fail
    exit_code = Column(Integer, nullable=True)
    operator = Column(String(100), nullable=True)
    params_json = Column(Text, nullable=True)
    log_path = Column(String(500), nullable=True)

    script = relationship("ScriptItem", back_populates="exec_records")

