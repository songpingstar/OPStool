# OPStool
运维脚本管理

## 功能特性

- 脚本分类管理
- 脚本版本控制
- 脚本执行记录
- 用户认证系统

## 快速开始

### 1. 安装依赖

```powershell
pip install -r requirements.txt
```

### 2. 创建管理员用户

首次使用需要创建管理员用户：

```powershell
python scripts/create_admin.py <用户名> <密码>
```

示例：
```powershell
python scripts/create_admin.py admin mypassword123
python scripts/create_admin.py admin mypassword123 --update
```

### 3. 启动应用

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问应用

打开浏览器访问：http://localhost:8000

使用创建的管理员账号登录即可使用。

## 用户认证

- 所有页面和 API 都需要登录后才能访问
- 未登录用户访问时会自动重定向到登录页面
- 登录后可以在页面右上角看到用户信息和登出按钮