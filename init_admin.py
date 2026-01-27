from sqlalchemy.orm import Session

from app import auth, models
from app.database import SessionLocal, engine, Base


def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == "admin").first()
        if not user:
            hashed_password = auth.get_password_hash("admin123")
            user = models.User(
                username="admin",
                hashed_password=hashed_password,
                email="admin@example.com",
                is_active=True,
                is_superuser=True,
            )
            db.add(user)
            db.commit()
            print("默认管理员用户创建成功！")
            print("用户名: admin")
            print("密码: admin123")
            print("请登录后立即修改密码！")
        else:
            print("管理员用户已存在，跳过创建")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
