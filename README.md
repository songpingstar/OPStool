# 运维工具箱

一个基于 FastAPI 的运维脚本管理工具，用于集中管理和执行常用的运维脚本。

## 功能特性

- 脚本分类管理
- 脚本版本控制
- 脚本在线编辑
- 脚本执行记录
- 用户认证与权限管理
- 支持 Python、PowerShell、Shell 等多种脚本类型

## 技术栈

- **后端框架**: FastAPI 0.115.0
- **数据库**: SQLite
- **ORM**: SQLAlchemy 2.0.35
- **模板引擎**: Jinja2
- **认证**: JWT + bcrypt
- **Web 服务器**: Uvicorn

### 登录系统

1. 访问 http://localhost:8000
2. 输入用户名和密码
3. 点击"登录"按钮

## 项目结构

```
OPStool/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI 应用主文件
│   ├── models.py        # 数据库模型
│   ├── schemas.py       # Pydantic 模型
│   ├── database.py      # 数据库连接配置
│   ├── executor.py      # 脚本执行器
│   └── auth.py         # 认证相关函数
├── templates/           # HTML 模板文件
│   ├── index.html
│   ├── login.html
│   ├── manage_scripts.html
│   └── script_detail.html
├── static/             # 静态资源
│   └── style.css
├── scripts/            # 脚本文件存储目录
├── logs/               # 执行日志存储目录
├── ops_toolbox.db      # SQLite 数据库文件
├── requirements.txt     # Python 依赖包列表
├── init_admin.py       # 初始化管理员账户脚本
└── README.md          # 项目说明文档
```

## 配置说明

### 数据库配置

默认使用 SQLite 数据库，数据库文件为 `ops_toolbox.db`。如需更换为其他数据库，请修改 `app/database.py` 中的数据库连接字符串。

### 认证配置

认证相关配置位于 `app/auth.py`：

- `SECRET_KEY`: JWT 密钥（生产环境请修改）
- `ALGORITHM`: 加密算法（默认 HS256）
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token 过期时间（默认 24 小时）

### 端口配置

默认端口为 8000，可通过启动命令的 `--port` 参数修改。

## 安全建议

1. 修改默认管理员密码
2. 更改 `app/auth.py` 中的 `SECRET_KEY`
3. 在生产环境中使用 HTTPS
4. 定期备份数据库文件
5. 对危险脚本操作添加二次确认

## 启动应用
```bash
uvicorn app.main:app --reload --port 8080
```
