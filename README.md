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

## 本地部署

### 环境要求

- Python 3.10+
- pip 包管理器

### 安装步骤

1. 克隆或下载项目到本地

2. 安装依赖包

```bash
pip install -r requirements.txt
```

3. 初始化数据库并创建默认管理员账户

```bash
python init_admin.py
```

执行后会显示默认管理员账户信息：
- 用户名: `admin`
- 密码: `admin123`

**重要**: 首次登录后请立即修改密码！

### 启动应用

开发模式（支持热重载）：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

生产模式：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 访问应用

启动成功后，在浏览器中访问：

```
http://localhost:8000
```

首次访问会自动跳转到登录页面，使用默认管理员账户登录。

## 使用说明

### 登录系统

1. 访问 http://localhost:8000
2. 输入用户名和密码
3. 点击"登录"按钮

### 脚本管理

#### 创建分类

1. 进入"脚本管理"页面
2. 在"新增分类"区域填写分类信息
3. 点击"创建分类"按钮

#### 创建脚本

1. 进入"脚本管理"页面
2. 在"新增脚本"区域填写脚本信息：
   - 所属分类（可选）
   - 标题
   - 描述
   - 类型（Python/PowerShell/Shell）
   - 脚本路径
   - 是否为危险操作
   - 初始内容（可选）
3. 点击"创建脚本"按钮

#### 编辑脚本

1. 在首页或脚本列表中点击脚本详情
2. 在代码编辑器中修改脚本内容
3. 点击"保存为新版本"按钮

#### 执行脚本

1. 进入脚本详情页面
2. 点击"运行脚本"按钮
3. 在执行记录中查看执行状态和日志

### 退出登录

点击页面右上角的"退出登录"按钮即可退出系统。

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

## 常见问题

### 无法启动应用

检查端口 8000 是否被占用，或使用其他端口启动：

```bash
uvicorn app.main:app --reload --port 8080
```

### 登录失败

确认用户名和密码是否正确，检查数据库中是否存在该用户。

### 脚本执行失败

检查脚本路径是否正确，脚本文件是否存在，以及脚本语法是否正确。

## 许可证

本项目仅供内部使用。

## 联系方式

如有问题或建议，请联系开发团队。
