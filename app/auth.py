from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import models
from .database import get_db

SECRET_KEY = "your-secret-key-here-change-in-production"  # 在生产环境中应该从环境变量读取


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        # 确保密码是字节串
        if isinstance(plain_password, str):
            plain_password = plain_password.encode('utf-8')
        # 确保哈希值是字节串
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    # 确保密码是字节串
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    # bcrypt 限制密码长度为 72 字节
    if len(password) > 72:
        password = password[:72]
    
    # 生成盐并哈希密码
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password, salt)
    
    # 返回字符串格式的哈希值
    return hashed.decode('utf-8')


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """验证用户凭证"""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> models.User:
    """从 Session 获取当前用户"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """从 Session 获取当前用户（可选，用于页面路由）"""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_active:
        return None
    return user
