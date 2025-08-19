# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 技术栈

### 后端框架

- **FastAPI** - 主要的 Web 框架，用于构建 API
- **SQLModel/SQLAlchemy** - 数据库 ORM 和数据建模
- **Pydantic** - 数据验证和设置管理
- **Jinja2** - HTML 模板引擎
- **AuthLib** - OIDC/OAuth2 认证库
- **Python-JOSE** - JWT Token 处理

### 前端技术

- **Fomantic UI 2.9.4** - 基于 Semantic UI 的响应式 UI 框架
- **jQuery 3.1.1** - JavaScript 库，用于 DOM 操作和事件处理
- **DOMPurify 2.4.0** - XSS 防护的 DOM 净化库
- **Marked 16.1.1** - Markdown 解析和渲染库

### 数据库

- **MySQL** - 主数据库
- **PyMySQL** - Python MySQL 驱动/连接器
- **Redis** - 会话存储和缓存数据库

### 开发工具

- **Uvicorn** - 用于运行应用程序的 ASGI 服务器
- **Black** - 代码格式化工具（在 VS Code 中配置）
- **VS Code** - 推荐的开发环境

## 项目结构

```
webhook-proxy/
├── app/                    # 主应用程序目录（后端API）
│   ├── dependencies.py     # 共享依赖（数据库会话管理、认证）
│   ├── main.py            # FastAPI应用程序入口点
│   ├── internal/          # 内部管理模块
│   │   └── admin.py       # 管理员路由和功能
│   ├── models/            # 数据模型
│   │   ├── jms_reqlog.py  # JMS请求日志模型
│   │   └── feishu_reqlog.py # 飞书请求日志模型
│   ├── routers/           # API路由处理器
│   │   ├── auth.py        # 认证相关路由（JWT + Session + OIDC）
│   │   ├── bot_webhook.py # Bot Webhook路由
│   │   ├── feishu.py      # 飞书Webhook代理路由
│   │   ├── items.py       # 项目相关路由
│   │   ├── jms_reqlog.py  # JMS日志路由
│   │   └── users.py       # 用户相关路由
│   ├── services/          # 服务层模块
│   │   ├── webhook_mapping.py # Webhook映射服务
│   │   └── redis_session.py   # Redis会话管理服务
│   └── utils/             # 工具模块
│       └── template_filters.py # Jinja2模板过滤器
├── templates/             # HTML模板文件（前端页面）
│   ├── alert/             # 警告/通知模板目录
│   ├── base_head.html     # 基础模板头部
│   ├── base_foot.html     # 基础模板底部
│   ├── base_menu.html     # 基础模板菜单
│   ├── dashboard.html     # 用户仪表板页面
│   ├── login.html         # 登录页面
│   └── cmdb/              # CMDB相关模板
│       └── show.html      # 显示页面模板
├── static/                # 静态资源目录（前端资源）
│   └── plugin/            # 前端插件库
│       ├── fomantic-ui-2.9.4/    # UI框架
│       ├── jquery-3.1.1/         # jQuery库
│       ├── dompurify-2.4.0/      # DOM净化库
│       └── markdown-16.1.1/      # Markdown解析库
├── config/                # 配置模块
│   ├── config.py          # Pydantic设置配置
│   └── webhook_mapping.yaml # Webhook映射配置文件
├── sql/                   # 数据库脚本
│   └── db.sql            # 数据库初始化脚本
├── requirements.txt       # Python依赖包
├── clearcache.sh         # 缓存清理脚本
├── startup.sh            # 应用启动脚本
├── CLAUDE.md             # Claude Code指导文档
└── README.md             # 项目文档
```

## 架构概述

这是一个全栈 FastAPI 应用程序，主要功能包括：

- **Webhook 代理服务**: 接收并转发各种系统的 Webhook 请求
- **请求日志记录**: 记录和管理来自 JMS（Jump Server）和飞书等系统的 HTTP 请求/响应数据
- **用户认证系统**: 支持 JWT、Session 和 OIDC 三种认证方式的多层次权限管理
- **Web 管理界面**: 提供直观的 Web 界面进行日志查看和系统管理

应用程序采用前后端分离的架构，后端提供 RESTful API，前端提供 Web 界面，具有清晰的关注点分离。

### 核心组件

**后端组件：**

- **主应用程序** (`app/main.py`): 带有路由注册的 FastAPI 应用
- **配置** (`config/config.py`): 带有数据库连接和应用配置的 Pydantic 设置
- **模型** (`app/models/`): 基于 SQLModel 的数据库实体数据模型
- **路由器** (`app/routers/`): 按功能组织的 API 端点处理器
- **依赖项** (`app/dependencies.py`): 包括数据库会话管理和认证在内的共享依赖项
- **服务层** (`app/services/`): 包含 Redis 会话管理和 Webhook 映射等业务逻辑服务
- **内部管理** (`app/internal/`): 管理员专用功能和路由

**前端组件：**

- **HTML 模板** (`templates/`): 基于 Jinja2 的 HTML 页面模板
- **静态资源** (`static/`): 前端 UI 框架和 JavaScript 库
  - **Fomantic UI**: 响应式 UI 框架
  - **jQuery**: JavaScript 库
  - **DOMPurify**: XSS 防护的 DOM 净化库
  - **Marked**: Markdown 解析库

### 数据库架构

应用程序使用 MySQL 和 SQLModel/SQLAlchemy 作为 ORM，Redis 作为会话存储。主要特点：

**MySQL 数据库:**

- 数据库连接在`config/config.py`中配置，连接字符串来自环境变量
- 主要数据实体包括：
  - `JMSReqLog`: 存储来自 JMS 系统的 HTTP 请求/响应数据
  - `FeishuReqLog`: 存储飞书 Webhook 代理的请求/响应数据
- 使用 JSON 列灵活存储标头和正文数据
- 时间戳存储为 Unix 时间戳

**Redis 会话存储:**

- 用于存储用户会话数据，支持过期时间管理
- 提供快速的会话查询和管理功能
- 支持集群部署时的会话共享
- 包含完整的会话生命周期管理（创建、读取、删除、清理）

### 关键数据模型

- **JMSReqLog**: 存储来自 JMS 系统的 HTTP 请求详细信息（方法、路径、标头、正文、状态等）
- **FeishuReqLog**: 存储飞书 Webhook 代理请求的详细信息（包括请求和响应数据）
- **User**: 用户认证和权限管理的用户实体（支持角色基础的访问控制）
- 所有模型遵循 SQLModel 模式，包含用于创建、更新和读取操作的独立类

### 关键服务组件

- **RedisSessionManager** (`app/services/redis_session.py`):

  - 提供完整的 Redis 会话管理功能
  - 支持会话创建、读取、删除和批量操作
  - 自动处理会话过期和清理
  - 包含管理员功能（查看所有会话、批量清理）

- **WebHookMapping** (`app/services/webhook_mapping.py`):
  - 处理 Webhook 请求的路由和映射逻辑
  - 支持配置文件驱动的映射规则

### API 结构

应用程序提供多个功能模块的 API 端点：

**认证模块 (`/auth/*`)**

- `POST /auth/token` - OAuth2 兼容的 JWT Token 获取
- `POST /auth/login` - Web 登录（设置 Session Cookie）
- `POST /auth/logout` - Web 登出（清除 Session）
- `GET /auth/me` - 获取当前用户信息（支持 JWT + Session）
- `GET /auth/me/jwt` - 获取当前用户信息（仅 JWT）
- `GET /auth/me/session` - 获取当前用户信息（仅 Session）
- `GET /auth/sessions` - 列出所有活跃会话（管理员）
- `DELETE /auth/sessions` - 清除所有会话（管理员）
- `GET /auth/login-page` - 登录页面（HTML）
- `GET /auth/dashboard` - 用户仪表板页面（HTML）
- `GET /auth/` - 根路径重定向

**JMS 请求日志模块 (`/jms_reqlog/*`)**

- `GET /jms_reqlog/` - 列出所有日志（HTML 页面，公开端点）
- `POST /jms_reqlog/` - 创建新日志条目（公开端点，用于接收 Webhook）
- `GET /jms_reqlog/list` - 分页日志列表（支持灵活认证）
- `GET /jms_reqlog/{id}` - 获取特定日志（需要认证）
- `PUT /jms_reqlog/{id}` - 更新日志条目（需要管理员权限）
- `DELETE /jms_reqlog/{id}` - 删除日志条目（需要管理员权限）

**飞书 Webhook 模块 (`/feishu/*`)**

- `POST /feishu/webhook/{webhook_id}` - 飞书 Webhook 代理端点
- `GET /feishu/logs` - 获取飞书 Webhook 日志
- `GET /feishu/logs/{log_id}` - 获取特定飞书 Webhook 日志

**其他端点**

- `GET /` - 根路径重定向到登录或仪表板
- `GET /login` - 重定向到登录页面
- `GET /dashboard` - 重定向到仪表板页面

### 认证

应用程序实现了多层次的认证系统：

**认证方式:**

- **JWT Token 认证**: 适用于 API 访问，通过 `Authorization: Bearer <token>` 头传递
- **Session Cookie 认证**: 适用于 Web 界面，使用 HttpOnly Cookie 存储会话信息
- **OIDC 认证**: 支持 OpenID Connect 单点登录集成

**认证级别:**

- **公开端点**: 无需认证，用于接收 Webhook 等
- **灵活认证端点**: 支持 JWT 或 Session 认证，提供不同功能级别
- **必需认证端点**: 要求用户必须通过 JWT 或 Session 认证
- **基于角色的端点**: 需要特定角色（如 admin）才能访问

**用户角色:**

- **user**: 普通用户角色
- **admin**: 管理员角色，可访问管理功能

### 配置

应用程序设置通过 Pydantic Settings 管理：

**数据库配置:**

- 数据库 URL 可通过环境变量配置
- 从`.env`文件加载设置
- 默认 MySQL 连接：`mysql+pymysql://root:mypassword@127.0.0.1/test2`

**Redis 配置 (会话管理):**

- `redis_host`: Redis 服务器地址 (默认: 127.0.0.1)
- `redis_port`: Redis 端口 (默认: 6379)
- `redis_db`: Redis 数据库索引 (默认: 13)
- `session_expire_seconds`: 会话过期时间 (默认: 86400 秒/24 小时)

**OIDC 配置 (单点登录):**

- `oidc_issuer_url`: OIDC 提供商的 Issuer URL
- `oidc_client_id`: OIDC 客户端 ID
- `oidc_client_secret`: OIDC 客户端密钥
- `oidc_redirect_uri`: OIDC 回调地址
- `oidc_scope`: OIDC 授权范围 (默认: "openid profile email")

## 开发指南

### 文件组织

**后端组织：**

- 遵循模块化 FastAPI 结构，清晰分离关注点
- 将模型保存在`app/models/`目录中
- 按功能在`app/routers/`中组织 API 端点
- 将共享依赖项放在`app/dependencies.py`中

**前端组织：**

- HTML 模板存放在`templates/`目录中
- 静态资源（CSS、JS、图片）存放在`static/`目录中
- 第三方前端库存放在`static/plugin/`目录中
- 遵循模板继承模式，使用基础模板组件

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
