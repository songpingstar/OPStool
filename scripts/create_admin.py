"""
创建或更新管理员用户脚本

使用方法:
    python scripts/create_admin.py <username> <password> [--update]

参数:
    username: 用户名
    password: 密码
    --update: 可选，如果用户已存在则更新密码

示例:
    python scripts/create_admin.py admin mypassword123
    python scripts/create_admin.py admin newpassword123 --update
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal
from app.models import User
from app.auth import get_password_hash


def create_or_update_admin_user(username: str, password: str, update_if_exists: bool = False):
    """创建或更新管理员用户"""
    db = SessionLocal()
    try:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        
        if existing_user:
            if not update_if_exists:
                print(f"错误: 用户名 '{username}' 已存在")
                print(f"提示: 使用 --update 参数可以更新密码")
                print(f"示例: python scripts/create_admin.py {username} <新密码> --update")
                return False
            
            # 更新密码
            hashed_password = get_password_hash(password)
            existing_user.hashed_password = hashed_password
            existing_user.is_active = True
            db.commit()
            db.refresh(existing_user)
            
            print(f"成功更新用户密码: {username}")
            print(f"用户ID: {existing_user.id}")
            return True
        else:
            # 创建新用户
            hashed_password = get_password_hash(password)
            new_user = User(
                username=username,
                hashed_password=hashed_password,
                is_active=True
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            print(f"成功创建管理员用户: {username}")
            print(f"用户ID: {new_user.id}")
            return True
    except Exception as e:
        db.rollback()
        print(f"操作失败: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("使用方法: python scripts/create_admin.py <username> <password> [--update]")
        print("示例:")
        print("  创建用户: python scripts/create_admin.py admin mypassword123")
        print("  更新密码: python scripts/create_admin.py admin newpassword123 --update")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    update_if_exists = "--update" in sys.argv or "-u" in sys.argv
    
    if not username or not password:
        print("错误: 用户名和密码不能为空")
        sys.exit(1)
    
    if len(password) < 6:
        print("警告: 密码长度建议至少6位")
        response = input("是否继续? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    success = create_or_update_admin_user(username, password, update_if_exists)
    sys.exit(0 if success else 1)
