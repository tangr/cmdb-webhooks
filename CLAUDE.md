# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 技术栈

### 后端框架

- **FastAPI** - 主要的 Web 框架，用于构建 API
- **SQLModel/SQLAlchemy** - 数据库 ORM 和数据建模
- **Pydantic** - 数据验证和设置管理

### 数据库

- **MySQL** - 主数据库
- **PyMySQL** - Python MySQL 驱动/连接器

### 开发工具

- **Uvicorn** - 用于运行应用程序的 ASGI 服务器
- **Black** - 代码格式化工具（在 VS Code 中配置）
- **VS Code** - 推荐的开发环境

## 项目结构

```
webhook-proxy/
├── app/                    # 主应用程序目录
│   ├── dependencies.py     # 共享依赖（数据库会话管理）
│   ├── main.py            # FastAPI应用程序入口点
│   ├── internal/          # 内部模块
│   │   └── admin.py       # 管理员相关功能
│   ├── models/            # 数据模型
│   │   └── jms_reqlog.py  # JMS请求日志模型
│   └── routers/           # API路由处理器
│       ├── items.py       # 项目相关路由
│       ├── jms_reqlog.py  # JMS日志路由
│       └── users.py       # 用户相关路由
├── config/                # 配置模块
│   └── config.py          # Pydantic设置配置
├── sql/                   # 数据库脚本
│   └── db.sql            # 数据库初始化脚本
├── requirements.txt       # Python依赖包
├── clearcache.sh         # 缓存清理脚本
├── startup.sh            # 应用启动脚本
├── CLAUDE.md             # Claude Code指导文档
└── README.md             # 项目文档
```

## 架构概述

这是一个 FastAPI 应用程序，用作 JMS（Jump Server）系统的 webhook 接收器和请求记录器。应用程序采用模块化的 FastAPI 结构，具有清晰的关注点分离。

### 核心组件

- **主应用程序** (`app/main.py`): 带有路由注册的 FastAPI 应用
- **配置** (`config/config.py`): 带有数据库连接和应用配置的 Pydantic 设置
- **模型** (`app/models/`): 基于 SQLModel 的数据库实体数据模型
- **路由器** (`app/routers/`): 按功能组织的 API 端点处理器
- **依赖项** (`app/dependencies.py`): 包括数据库会话管理在内的共享依赖项

### 数据库架构

应用程序使用 MySQL 和 SQLModel/SQLAlchemy 作为 ORM。主要特点：

- 数据库连接在`config/config.py`中配置，连接字符串来自环境变量
- 主要实体是`JMSReqLog`，存储来自 JMS 系统的 HTTP 请求/响应数据
- 使用 JSON 列灵活存储标头和正文数据
- 时间戳存储为 Unix 时间戳

### 关键数据模型

- **JMSReqLog**: 存储 HTTP 请求详细信息的主要记录实体（方法、路径、标头、正文、状态等）
- 模型遵循 SQLModel 模式，包含用于创建、更新和读取操作的独立类

### API 结构

应用程序为请求日志提供 CRUD 操作：

- `GET /jms_reqlog/` - 列出所有日志
- `GET /jms_reqlog/list` - 分页日志列表
- `POST /jms_reqlog/` - 创建新日志条目
- `GET /jms_reqlog/{id}` - 获取特定日志
- `PUT /jms_reqlog/{id}` - 更新日志条目
- `DELETE /jms_reqlog/{id}` - 删除日志条目

### 认证

实现了基本的基于 Token 的认证：

- 管理员端点需要值为`fake-super-secret-token`的`X-Token`头
- 查询 Token 认证可用但当前已禁用

### 配置

应用程序设置通过 Pydantic Settings 管理：

- 数据库 URL 可通过环境变量配置
- 从`.env`文件加载设置
- 默认 MySQL 连接：`mysql+pymysql://root:mypassword@127.0.0.1/test2`

## 开发指南

### 文件组织

- 遵循模块化 FastAPI 结构，清晰分离关注点
- 将模型保存在`app/models/`目录中
- 按功能在`app/routers/`中组织 API 端点
- 将共享依赖项放在`app/dependencies.py`中

### 代码风格

- 使用 Black 格式化程序确保代码格式一致
- 遵循 FastAPI 和 SQLModel 最佳实践
- 在创建、读取和更新模型类之间保持清晰分离

### 数据库

- 对所有数据库模型使用 SQLModel
- 将灵活数据（标头、请求正文）存储为 JSON 列
- 对时间相关字段使用 Unix 时间戳

## 重要说明

### 代码注释规范

- 所有代码内的注释必须使用英文
- 项目文档和配置说明可以使用中文
- 保持代码的国际化兼容性
