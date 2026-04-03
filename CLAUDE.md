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
- **Amis 6.13.0** - 百度低代码前端框架，用于动态表单渲染

### 数据库

- **MySQL** - 主数据库
- **PyMySQL** - Python MySQL 驱动/连接器
- **Redis** - 会话存储和缓存数据库

### 开发工具

- **Uvicorn** - 用于运行应用程序的 ASGI 服务器
- **Black** - 代码格式化工具（在 VS Code 中配置）
- **VS Code** - 推荐的开发环境

## 项目结构

```text
webhook-proxy/
├── app/                    # 主应用程序目录（后端API）
│   ├── dependencies.py     # 共享依赖（数据库会话管理、认证）
│   ├── main.py            # FastAPI应用程序入口点
│   ├── internal/          # 内部管理模块
│   │   └── admin.py       # 管理员路由和功能
│   ├── models/            # 数据模型
│   │   ├── cmdb_trigger_reqlog.py  # CMDB Trigger请求日志模型
│   │   ├── feishu_bot_reqlog.py # 飞书机器人请求日志模型
│   │   ├── gitlab_hook_reqlog.py # GitLab Hook请求日志模型
│   │   ├── amis_jenkins_reqlog.py # Amis Jenkins请求日志模型
│   │   ├── feishu_approval_reqlog.py # 飞书审批请求日志模型
│   │   └── pending_jenkins_job.py # 待执行Jenkins任务模型（审批关联）
│   ├── routers/           # API路由处理器
│   │   ├── auth.py        # 认证相关路由（JWT + Session + OIDC）
│   │   ├── cmdb_trigger.py        # CMDB Trigger日志路由
│   │   ├── feishu_bot.py      # 飞书机器人Webhook代理路由
│   │   ├── gitlab_hook.py      # GitLab Hook Webhook代理路由
│   │   ├── amis_jenkins.py    # Amis Jenkins表单代理路由
│   │   ├── harbor_artifacts.py # Harbor镜像Artifacts查询路由
│   │   └── feishu_approval.py # 飞书审批代理路由
│   ├── services/          # 服务层模块
│   │   ├── cmdb_trigger_service.py      # CMDB Trigger代理请求处理服务
│   │   ├── feishu_bot_service.py    # 飞书机器人服务逻辑
│   │   ├── gitlab_hook_service.py    # GitLab Hook到Jenkins转发服务
│   │   ├── amis_jenkins_service.py  # Amis Jenkins表单到Jenkins转发服务
│   │   ├── amis_jenkins_permissions.py # Amis Jenkins表单级别权限控制
│   │   ├── harbor_artifacts_service.py # Harbor镜像Artifacts查询服务
│   │   ├── feishu_client.py     # 飞书开放平台API客户端
│   │   ├── feishu_approval_service.py # 飞书审批代理服务
│   │   └── redis_session.py     # Redis会话管理服务
│   └── utils/             # 工具模块
│       ├── logger.py            # 日志工具
│       ├── template_filters.py  # Jinja2模板过滤器
│       └── webhook_security.py  # Webhook安全验证
├── templates/             # HTML模板文件（前端页面）
│   ├── base_head.html     # 基础模板头部
│   ├── base_foot.html     # 基础模板底部
│   ├── base_menu.html     # 基础模板菜单
│   ├── dashboard.html     # 用户仪表板页面
│   ├── login.html         # 登录页面
│   ├── cmdb/              # CMDB相关模板
│   │   └── show.html      # 显示页面模板
│   ├── feishu/            # 飞书相关模板目录
│   └── amis_jenkins/      # Amis Jenkins相关模板
│       ├── forms.html     # 表单列表页面
│       ├── form.html      # Amis表单渲染页面（Submit + History Tab）
│       ├── pending.html   # 待执行任务页面（跨表单总览）
│       └── _execute_modal.html  # 执行确认弹窗（共享模板片段）
├── static/                # 静态资源目录（前端资源）
│   ├── js/                # 自定义JavaScript
│   │   └── amis_jenkins_common.js  # Amis Jenkins共享模块（同步/执行/弹窗）
│   └── plugin/            # 前端插件库
│       ├── fomantic-ui-2.9.4/    # UI框架
│       ├── jquery-3.1.1/         # jQuery库
│       ├── dompurify-2.4.0/      # DOM净化库
│       ├── markdown-16.1.1/      # Markdown解析库
│       └── amis-6.13.0/          # Amis低代码框架
├── config/                # 配置模块
│   ├── config.py          # Pydantic设置配置
│   ├── gitlab_jenkins_mapping.yaml # GitLab到Jenkins映射配置文件
│   ├── amis_jenkins_mapping.yaml # Amis表单到Jenkins映射配置文件
│   ├── feishu_bot_config.yaml # 飞书机器人Webhook代理配置文件
│   ├── harbor_config.yaml # Harbor多实例配置文件
│   └── feishu_approval_config.yaml # 飞书审批应用配置文件
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
- **请求日志记录**: 记录和管理来自 CMDB Trigger、飞书机器人和 GitLab Hook 等系统的 HTTP 请求/响应数据
- **用户认证系统**: 支持 JWT、Session 和 OIDC 三种认证方式的多层次权限管理
- **Web 管理界面**: 提供直观的 Web 界面进行日志查看和系统管理
- **Amis Jenkins 表单代理**: 使用百度 Amis 低代码框架构建参数化表单 UI，替代 Jenkins 原生 parameters，支持动态表单渲染和 Jenkins 构建触发
- **Harbor 镜像查询服务**: 代理 Harbor Registry API，获取镜像 Artifacts 列表，为 Amis Select 组件提供数据源，支持多 Harbor 实例
- **飞书审批代理服务**: 代理飞书开放平台审批 API，支持发起审批单和查询审批状态，用于 DevOps CD 发布流程的审批关联

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
  - `CmdbTriggerReqLog`: 存储来自 CMDB Trigger 系统的 HTTP 请求/响应数据
  - `FeishuBotReqLog`: 存储飞书机器人 Webhook 代理的请求/响应数据
  - `GitlabHookReqLog`: 存储 GitLab Hook Webhook 到 Jenkins 的请求/响应数据
  - `AmisJenkinsReqLog`: 存储 Amis 表单提交到 Jenkins 的请求/响应数据
  - `FeishuApprovalReqLog`: 存储飞书审批代理的请求/响应数据
  - `PendingJenkinsJob`: 存储待执行的 Jenkins 任务（关联飞书审批，审批通过后手动执行）
- 使用 JSON 列灵活存储标头和正文数据
- 时间戳存储为 Unix 时间戳

**Redis 会话存储:**

- 用于存储用户会话数据，支持过期时间管理
- 提供快速的会话查询和管理功能
- 支持集群部署时的会话共享
- 包含完整的会话生命周期管理（创建、读取、删除、清理）

### 关键数据模型

- **CmdbTriggerReqLog**: 存储来自 CMDB Trigger 系统的 HTTP 请求详细信息（方法、路径、标头、正文、状态等）
- **FeishuBotReqLog**: 存储飞书机器人 Webhook 代理请求的详细信息（包括请求和响应数据）
- **GitlabHookReqLog**: 存储 GitLab Hook Webhook 请求详细信息（事件类型、项目路径、Jenkins 响应等）
- **AmisJenkinsReqLog**: 存储 Amis 表单提交到 Jenkins 的请求详细信息（表单 ID、触发类型、用户名、Jenkins 响应等）
- **FeishuApprovalReqLog**: 存储飞书审批代理请求详细信息（应用名称、审批码、飞书实例码、审批状态、表单数据、飞书响应等）
- **PendingJenkinsJob**: 存储待执行 Jenkins 任务（表单 ID、Jenkins 任务路径、请求参数、审批日志关联、执行状态、执行表单 Schema、执行次数、最大执行次数、过期时间等）
- **User**: 用户认证和权限管理的用户实体（支持角色基础的访问控制）
- 所有模型遵循 SQLModel 模式，包含用于创建、更新和读取操作的独立类

### 关键服务组件

- **RedisSessionManager** (`app/services/redis_session.py`):

  - 提供完整的 Redis 会话管理功能
  - 支持会话创建、读取、删除和批量操作
  - 自动处理会话过期和清理
  - 包含管理员功能（查看所有会话、批量清理）

- **CmdbTriggerService** (`app/services/cmdb_trigger_service.py`):

  - 处理 CMDB Trigger 代理请求的核心业务逻辑
  - 支持 API Key 验证和 IP 白名单校验
  - 转发 HTTP 请求到目标服务器（支持 GET/POST/PUT/DELETE/PATCH）
  - 记录请求/响应日志到数据库

- **FeishuBotService** (`app/services/feishu_bot_service.py`):

  - 处理飞书机器人 Webhook 代理请求的核心业务逻辑
  - 包含安全验证和请求转发功能
  - 支持 Grafana 告警格式自动转换为飞书卡片格式
  - 记录请求/响应日志

- **GitlabHookService** (`app/services/gitlab_hook_service.py`):
  - 处理 GitLab System Hook 到 Jenkins Generic Webhook Trigger 的转发
  - 支持 X-Gitlab-Token 验证
  - 自动预处理 GitLab payload 为标准化字段（Push/Tag Push/Merge Request）
  - 支持项目路径通配符匹配和字段过滤
  - 记录请求/响应日志到数据库

- **AmisJenkinsService** (`app/services/amis_jenkins_service.py`):
  - 处理 Amis 表单提交到 Jenkins 的转发
  - 支持两种 Jenkins 触发方式：Generic Webhook Trigger 和 Remote API (buildWithParameters)
  - 从 YAML 配置文件加载表单定义和 Jenkins 映射
  - 支持表单级别覆盖全局 Jenkins 配置
  - 记录请求/响应日志到数据库
  - **飞书审批集成**：支持表单提交前的审批流程
    - 审批配置通过 `approval` 节点启用
    - 自动创建飞书审批并保存待执行任务
    - 支持审批状态同步和审批后手动执行
  - 用户飞书 ID 映射：通过 `user_feishu_mapping` 配置，未配置时默认使用登录用户名
  - **合并历史查询**：`get_form_history` 合并 AmisJenkinsReqLog 和 PendingJenkinsJob 按时间倒序展示
    - History Tab 内嵌同步审批状态和执行功能（无需跳转 Pending 页面）
    - 返回 `can_execute`、`execution_form_schema`、`approval_status` 等字段
  - **Jenkins Build URL 解析**：触发构建后自动解析 Build URL
    - 从 Jenkins 响应中捕获 queue URL（Generic Webhook: response body `jobs[].url`; Remote API: `Location` header）
    - 内联等待后查询 Jenkins queue API (`/queue/item/{id}/api/json`) 获取 build number
    - 支持 Console Output 和 Blue Ocean 两种 URL 格式
    - 解析结果以 `_queue_url`、`_build_number`、`_build_url` 存入 `jenkins_response` JSON
    - 支持手动重试解析（前端 "Get Build URL" 按钮）
    - 等待时间和 URL 格式支持全局配置和表单级别覆盖
  - **表单级别权限控制**：通过 `permissions` 配置实现 RBAC
    - 权限检查逻辑集中在 `app/services/amis_jenkins_permissions.py`
    - 支持 `allowed_roles`/`allowed_users`（查看+提交）和 `execute_roles`/`execute_users`（执行）
    - admin 角色自动绕过所有权限检查
    - 未配置 `permissions` 的表单默认仅 admin 可访问

- **HarborArtifactsService** (`app/services/harbor_artifacts_service.py`):
  - 代理 Harbor Registry API 获取镜像 Artifacts 列表
  - 支持多 Harbor 实例配置（通过 YAML 配置文件）
  - 使用 Robot Account Token 进行 Harbor API 认证
  - 自动格式化返回数据为 Amis Select 组件所需格式
  - 支持分页查询和按推送时间排序
  - 处理带/不带 Tag 的 Artifacts（无 Tag 时显示 Digest）

- **FeishuClient** (`app/services/feishu_client.py`):
  - 飞书开放平台 API 客户端
  - 自动管理 tenant_access_token（获取、缓存、刷新）
  - 提供审批实例创建和状态查询 API
  - 支持多个飞书应用配置（从 YAML 配置文件加载）
  - 类级别 Token 缓存，避免重复请求

- **FeishuApprovalService** (`app/services/feishu_approval_service.py`):
  - 处理飞书审批代理请求的核心业务逻辑
  - 封装 FeishuClient 提供高级审批操作
  - 支持发起审批单和查询审批状态
  - 自动同步飞书审批状态到本地数据库
  - 记录请求/响应日志到数据库
  - 支持按用户名、应用名、状态过滤审批记录

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
- `GET /auth/oidc/login` - OIDC 登录重定向
- `GET /auth/oidc/callback` - OIDC 回调处理
- `GET /auth/` - 根路径重定向

**CMDB Trigger 请求日志模块 (`/cmdb-trigger/*`)**

- `GET /cmdb-trigger/` - 列出所有日志（HTML 页面，需要认证）
- `POST /cmdb-trigger/` - 创建新日志条目（公开端点，用于接收 Webhook）
- `GET /cmdb-trigger/logs` - 分页日志列表（需要认证）
- `GET /cmdb-trigger/{log_id}` - 获取特定日志（需要认证）
- `PUT /cmdb-trigger/{log_id}` - 更新日志条目（需要管理员权限）
- `DELETE /cmdb-trigger/{log_id}` - 删除日志条目（需要管理员权限）

**飞书机器人 Webhook 模块 (`/feishu-bot/*`)**

- `POST /feishu-bot/webhook/proxy/{webhook_id}` - 飞书机器人 Webhook 代理端点（按 ID）
- `POST /feishu-bot/webhook/alias/{webhook_name}` - 飞书机器人 Webhook 代理端点（按名称别名）
- `GET /feishu-bot/logs` - 获取飞书机器人 Webhook 日志列表
- `GET /feishu-bot/logs/{log_id}` - 获取特定飞书机器人 Webhook 日志

**GitLab Hook Webhook 模块 (`/gitlab-hook/*`)**

- `POST /gitlab-hook/webhook` - GitLab System Hook 接收端点，转发到 Jenkins Generic Webhook Trigger
- `GET /gitlab-hook/logs` - 获取 GitLab Hook Webhook 日志列表（需要认证）
- `GET /gitlab-hook/logs/{log_id}` - 获取特定 GitLab Hook Webhook 日志（需要认证）

**Amis Jenkins 表单模块 (`/amis-jenkins/*`)**

- `GET /amis-jenkins/forms` - 表单列表页面（HTML，需要认证）
- `GET /amis-jenkins/forms/{form_id}` - Amis 表单页面（HTML，需要认证，Tab 切换：Submit 提交表单 / History 提交历史+同步+执行）
- `GET /amis-jenkins/api/forms` - 获取所有表单列表（API，需要认证）
- `GET /amis-jenkins/api/schema/{form_id}` - 获取表单 Amis Schema（API，需要认证）
- `POST /amis-jenkins/api/submit/{form_id}` - 提交表单到 Jenkins（API，需要认证）
  - 若启用审批：创建飞书审批 + 待执行任务记录
  - 若未启用审批：直接触发 Jenkins 构建
- `GET /amis-jenkins/api/history/{form_id}` - 获取表单合并历史记录（API，需要认证）
  - 合并 AmisJenkinsReqLog（已执行日志）和 PendingJenkinsJob（审批任务），按时间倒序
  - Query 参数：`skip`、`limit`
  - 返回统一格式，`source` 字段区分来源（`log` 或 `pending`）
- `GET /amis-jenkins/logs` - 获取 Amis Jenkins 日志列表（需要认证）
  - Query 参数：`form_id`（可选，按表单过滤）、`skip`、`limit`
- `GET /amis-jenkins/logs/{log_id}` - 获取特定 Amis Jenkins 日志（需要认证）
- `GET /amis-jenkins/pending` - 待执行任务页面（HTML，需要认证）
- `GET /amis-jenkins/api/pending` - 获取待执行任务列表（API，需要认证）
  - Query 参数：`username`、`status`、`skip`、`limit`
  - status 可选值：`pending_approval`、`approved`、`completed`、`exhausted`、`expired`、`executed`、`rejected`、`canceled`
- `GET /amis-jenkins/api/pending/{job_id}` - 获取特定待执行任务详情（需要认证）
- `POST /amis-jenkins/api/pending/{job_id}/sync` - 同步审批状态（从飞书获取最新状态）
- `POST /amis-jenkins/api/pending/{job_id}/cancel` - 手动取消任务（仅 `pending_approval` 状态）
- `POST /amis-jenkins/api/pending/{job_id}/complete` - 手动完成任务（仅 `approved` 状态）
- `POST /amis-jenkins/api/pending/{job_id}/execute` - 执行已审批任务（触发 Jenkins 构建）
- `POST /amis-jenkins/api/resolve-build-url` - 手动重试解析 Jenkins Build URL
  - Query 参数：`source`（`log` 或 `pending`）、`id`（记录 ID）
  - 从已存储的 queue URL 查询 Jenkins queue API 获取 build number 并构建 Build URL
  - 成功后自动更新数据库记录的 `jenkins_response` 中的 `_build_number` 和 `_build_url`

**Harbor Artifacts 模块 (`/harbor-artifacts/*`)**

- `GET /harbor-artifacts` - 获取镜像 Artifacts 列表（需要认证）
  - Query 参数：`instance`（Harbor 实例 ID）、`project`（项目名）、`repo`（仓库路径）、`page`、`page_size`
  - 返回 Amis Select 兼容格式：`{status, msg, data: {options: [{label, value}], hasMore, page, pageSize}}`
- `GET /harbor-artifacts/instances` - 列出可用的 Harbor 实例（需要认证）

**飞书审批代理模块 (`/feishu-approval/*`)**

- `GET /feishu-approval/apps` - 获取可用的飞书应用列表（需要认证）
- `POST /feishu-approval/create` - 发起审批单（需要认证）
  - 请求参数：`app_name`（应用名称）、`feishu_user_id`（飞书用户 ID）、`form_data`（表单数据）、`approval_code`（可选，审批定义码）
  - 返回：`{status, msg, data: {success, log_id, feishu_instance_code, status}}`
- `GET /feishu-approval/status/{log_id}` - 按数据库 ID 查询审批状态（需要认证）
- `GET /feishu-approval/status/instance/{instance_code}` - 按飞书实例码查询审批状态（需要认证）
  - Query 参数：`app_name`（默认 "default"）
- `GET /feishu-approval/logs` - 获取审批记录列表（需要认证）
  - Query 参数：`username`、`app_name`、`status`、`skip`、`limit`
- `GET /feishu-approval/logs/{log_id}` - 获取特定审批记录（需要认证）

**其他端点:**

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

**Webhook 安全配置:**

- `cmdb_trigger_webhook_api_keys`: CMDB Trigger Webhook API Keys（逗号分隔，空值表示不验证）
- `webhook_ip_whitelist`: Webhook 请求 IP 白名单（支持单 IP 和 CIDR 格式）

**登录选项配置:**

- `enable_username_password_login`: 启用/禁用用户名密码登录 (默认: true)
- `enable_oidc_login`: 启用/禁用 OIDC 登录 (默认: true)

**Redis 配置 (会话管理):**

- `redis_host`: Redis 服务器地址 (默认: 127.0.0.1)
- `redis_port`: Redis 端口 (默认: 6379)
- `redis_db`: Redis 数据库索引 (默认: 13)
- `redis_password`: Redis 密码 (默认: 空)
- `redis_max_connections`: 最大连接数 (默认: 10)
- `redis_decode_responses`: 自动解码响应 (默认: true)
- `session_redis_key_prefix`: 会话 Key 前缀 (默认: "session:")
- `session_expire_seconds`: 会话过期时间 (默认: 86400 秒/24 小时)

**OIDC 配置 (单点登录):**

- `oidc_issuer_url`: OIDC 提供商的 Issuer URL
- `oidc_client_id`: OIDC 客户端 ID
- `oidc_client_secret`: OIDC 客户端密钥
- `oidc_redirect_uri`: OIDC 回调地址
- `oidc_scope`: OIDC 授权范围 (默认: "openid profile email")
- `oidc_username_attribute`: 用户名属性字段 (默认: "preferred_username")
- `oidc_login_button_text`: OIDC 登录按钮文本 (默认: "Sign in with OIDC")

**角色映射配置:**

- `oidc_role_mapping`: OIDC 用户角色映射（用户名到角色的映射字典）
- `mock_users`: 模拟用户数据库（用于开发和测试环境）

**菜单可见性配置:**

- `menu_visibility`: 菜单项可见性配置（菜单 ID 到允许角色列表的映射）
  - 格式：`{menu_id: [allowed_role_1, allowed_role_2, ...]}`
  - 未配置的菜单项默认隐藏
  - 默认值：`{"cmdb": ["admin"], "amis_jenkins": ["admin"]}`
  - 示例：`{"cmdb": ["admin"], "amis_jenkins": ["admin", "deploy-prod", "deploy-staging"]}`

**GitLab Webhook 配置:**

- `gitlab_hook_webhook_secret_tokens`: GitLab Secret Token（逗号分隔，空值表示不验证）
- `gitlab_hook_enable_push_events`: 启用 Push 事件处理 (默认: true)
- `gitlab_hook_enable_tag_push_events`: 启用 Tag Push 事件处理 (默认: false，预留)
- `gitlab_hook_enable_merge_request_events`: 启用 Merge Request 事件处理 (默认: false，预留)

**GitLab-Jenkins 映射配置 (`config/gitlab_jenkins_mapping.yaml`):**

- `jenkins_base_url`: Jenkins 服务器 URL（全局配置）
- `jenkins_default_token`: 默认 Jenkins 触发 Token（映射中未配置 token 时使用）
- 支持按项目路径配置 Jenkins 任务映射
- 支持通配符模式匹配（如 `group/*`）
- 映射中可覆盖 `jenkins_base_url` 和 `jenkins_token`（指向不同 Jenkins 服务器）
- 自动预处理 GitLab payload 为标准化字段
- 支持 `include_fields` 限制发送的字段
- 支持 `extra_params` 添加额外静态参数

**日志配置:**

- `log_level`: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `log_format`: 日志格式字符串
- `log_to_file`: 是否输出到文件 (默认: false)
- `log_max_bytes`: 日志文件最大字节数 (默认: 10MB)
- `log_backup_count`: 日志文件备份数量 (默认: 5)
- `enable_database_logging`: 启用数据库日志记录 (默认: true)
- `enable_console_logging`: 启用控制台日志输出 (默认: false)

**Amis-Jenkins 映射配置 (`config/amis_jenkins_mapping.yaml`):**

- `jenkins_base_url`: Jenkins 服务器 URL（全局配置）
- `jenkins_default_token`: 默认 Jenkins Generic Webhook 触发 Token
- `jenkins_default_user`: 默认 Jenkins 用户名（用于 Remote API 触发和 Queue API 查询）
- `jenkins_default_api_token`: 默认 Jenkins API Token（用于 Remote API 触发和 Queue API 查询）
- `jenkins_build_url_format`: Build URL 格式（`console` 或 `blueocean`，默认: `console`）
- `jenkins_queue_resolve_delay`: 触发构建后等待几秒再查询 Queue API 获取 build number（默认: 3，0 = 禁用）
- `user_feishu_mapping`: 用户名到飞书用户 ID 的映射（用于审批功能）
  - 未配置的用户默认使用登录用户名作为飞书用户 ID
- 支持多个表单定义，每个表单包含：
  - `title`: 表单显示标题
  - `description`: 表单描述
  - `jenkins_job`: Jenkins 任务路径
  - `trigger_type`: 触发类型 (`generic_webhook` 或 `remote_api`)
  - `jenkins_token`: 表单级别的 Jenkins Token（可选，覆盖全局配置，用于 Generic Webhook 触发）
  - `jenkins_user`: 表单级别的 Jenkins 用户（可选，覆盖全局配置，用于 Remote API 触发和 Queue API 查询）
  - `jenkins_api_token`: 表单级别的 Jenkins API Token（可选，覆盖全局配置，用于 Remote API 触发和 Queue API 查询）
  - `jenkins_base_url`: 表单级别的 Jenkins URL（可选，覆盖全局配置）
  - `jenkins_build_url_format`: 表单级别的 Build URL 格式（可选，覆盖全局配置）
  - `jenkins_queue_resolve_delay`: 表单级别的 Queue API 等待时间（可选，覆盖全局配置）
  - `approval`: 飞书审批配置（可选）
    - `enabled`: 是否启用审批（true/false）
    - `feishu_app`: 飞书应用名称（对应 `feishu_approval_config.yaml` 中的配置）
    - `approval_code`: 审批定义码（可选，覆盖应用默认配置）
    - `form_data_template`: 表单数据模板，映射飞书审批控件 ID 到值
    - `modifiable_fields`: 可修改字段列表（审批后执行时可修改的字段）
    - `max_executions`: 最大执行次数（0 = 无限制，默认: 0）
    - `expire_hours`: 审批过期时间（小时，0 = 永不过期，默认: 0）
  - `permissions`: 表单级别权限控制（可选，未配置时仅 admin 可访问）
    - `allowed_roles`: 可查看和提交的角色列表（主要方式，角色在 `oidc_role_mapping` 中定义）
    - `allowed_users`: 可查看和提交的用户列表（补充方式）
    - `execute_roles`: 可执行他人待审批任务的角色列表（可选，需同时在 `allowed_roles` 中）
    - `execute_users`: 可执行他人待审批任务的用户列表（可选，需同时在 `allowed_users` 中）
    - 注意：admin 角色始终拥有所有表单的完整权限，无需配置
  - `schema`: Amis 表单 Schema（JSON/YAML 格式）

**飞书机器人配置 (`config/feishu_bot_config.yaml`):**

- `feishu_bot_webhook_base_url`: 飞书机器人 Webhook 基础 URL（默认: `https://open.feishu.cn/open-apis/bot/v2/hook/`）
- `feishu_bot_webhook_api_keys`: Webhook API Keys 列表（列表格式，空列表表示不验证）
- `feishu_bot_webhook_mappings`: Webhook ID 到名称的映射（用于 `/webhook/alias/{webhook_name}` 别名路由）

**Harbor 配置 (`config/harbor_config.yaml`):**

- `instances`: Harbor 实例配置（支持多实例）
  - 每个实例包含：
    - `base_url`: Harbor 服务器 URL
    - `robot_token`: Robot Account Token（格式：`robot$name:secret`）
    - `timeout`: 请求超时时间（可选，覆盖默认值）
- `default_instance`: 默认 Harbor 实例 ID（未指定 instance 参数时使用）
- `default_page_size`: 默认每页数量（默认: 50）
- `max_page_size`: 最大每页数量（默认: 100）
- `default_timeout`: 默认请求超时秒数（默认: 30）

**Amis Select 组件配置示例:**

```yaml
- type: "select"
  name: "image_tag"
  label: "Image Tag"
  required: true
  source: "/harbor-artifacts?instance=prod&project=${project}&repo=${service}"
```

**Amis Jenkins 权限配置示例:**

```yaml
# config/config.py 或 .env 中定义角色映射
oidc_role_mapping:
  admin: ["admin", "tangshoubin"]
  deploy-prod: ["alice", "bob", "charlie"]   # 生产部署角色
  deploy-staging: ["alice", "bob", "dev1"]   # 预发布部署角色

# config/amis_jenkins_mapping.yaml 中表单权限配置
forms:
  deploy-prod:
    title: "Deploy to Production"
    permissions:
      allowed_roles: ["deploy-prod"]          # 主要方式：按角色授权
      allowed_users: ["emergency-user"]       # 补充方式：直接指定用户
      execute_roles: ["deploy-prod"]          # 可执行待审批任务的角色
      execute_users: []                       # 可执行待审批任务的用户
    # ... jenkins_job, schema 等配置

  deploy-staging:
    title: "Deploy to Staging"
    permissions:
      allowed_roles: ["deploy-staging", "deploy-prod"]  # 多个角色
    # ... 其他配置

  admin-only-form:
    title: "Admin Tool"
    # 不配置 permissions = 仅 admin 可访问
    # ...
```

**权限规则说明：**

- **admin 角色**始终拥有所有表单的完整权限（查看、提交、执行），无需配置
- **未配置 `permissions`** 的表单默认仅 admin 可访问
- **`allowed_roles`**（主要方式）：角色在 `oidc_role_mapping` 中定义，映射到用户列表
- **`allowed_users`**（补充方式）：直接指定用户名，用于个别特殊用户
- **`execute_roles` / `execute_users`**：扩展执行权限（默认：提交者 + admin 可执行），前提是用户同时在 `allowed_roles`/`allowed_users` 中（需要能看到任务才能执行）
- 有表单权限的用户可以查看该表单的全部提交历史

**Amis Jenkins 审批配置示例:**

```yaml
# 用户到飞书 ID 映射
user_feishu_mapping:
  admin: "ce39af4f"
  tangshoubin: "ce39af4f"
  # 未配置的用户将使用其登录用户名作为飞书用户 ID

forms:
  deploy-prod:
    title: "Deploy to Production"
    jenkins_job: "deploy/prod"
    trigger_type: "generic_webhook"
    approval:
      enabled: true
      feishu_app: "yax-tmptest1"
      # form_data_template 将表单字段映射到飞书审批控件
      # 可用占位符: {form_id}, {form_title}, {jenkins_job}, {username}, {request_params_json}, {字段名}
      form_data_template:
        widget-id1: "表单: {form_title}\nJenkins任务: {jenkins_job}\n提交人: {username}"
        widget-id2: "项目: {project}\n环境: {environment}\n服务: {service}"
        widget-id3: "镜像Tag: {image_tag}\n备注: {comment}"
        widget-id4: "完整参数:\n{request_params_json}"
      # 多次执行配置（可选）
      modifiable_fields: ["environment", "comment"]  # 执行时可修改的字段
      max_executions: 5   # 最多执行 5 次（0 = 无限制）
      expire_hours: 24    # 24 小时后过期（0 = 永不过期）
    schema:
      # Amis schema...
```

**多次执行功能说明:**

当配置了 `modifiable_fields`、`max_executions` 或 `expire_hours` 时，一个审批单可以触发多次 Jenkins 执行：

- **modifiable_fields**: 列表中的字段在执行时可以修改（如切换部署环境）
  - 提交审批时，完整的 Amis 表单 Schema 会被快照保存到 `execution_form_schema`
  - 执行时使用 Amis 渲染表单：可修改字段可编辑，其他字段显示为静态（readonly）
  - 支持所有 Amis 字段类型，保留原始表单的 UI 和逻辑
- **max_executions**: 限制执行次数，达到限制后状态变为 `exhausted`
- **expire_hours**: 设置审批有效期，过期后状态变为 `expired`

**Pending Job 状态说明:**

| 状态 | 说明 |
|------|------|
| `pending_approval` | 等待审批 |
| `approved` | 已审批，可执行 |
| `completed` | 手动标记完成（审批通过后不再需要执行） |
| `exhausted` | 已达到最大执行次数 |
| `expired` | 已过期 |
| `rejected` | 审批被拒绝 |
| `canceled` | 审批前手动取消 |

**Jenkins Build URL 解析说明:**

触发 Jenkins 构建后，系统自动尝试解析 Build URL 并存储到 `jenkins_response` 中：

- 触发构建时捕获 queue URL（Generic Webhook: 从 response body `jobs` 字段; Remote API: 从 `Location` header）
- 等待 `jenkins_queue_resolve_delay` 秒后查询 Jenkins Queue API (`/queue/item/{id}/api/json`)
- 从 `executable.number` 获取 build number，拼接为 Console Output 或 Blue Ocean URL
- 解析结果存入 `jenkins_response` JSON（使用 `_` 前缀与 Jenkins 原始响应区分）：
  - `_queue_url`: Jenkins queue item URL
  - `_build_number`: 构建编号
  - `_build_url`: 完整的 Jenkins 构建 URL
- 若内联解析失败（构建尚未开始），前端显示 "Get Build URL" 按钮供手动重试
- Queue API 查询需要 Basic Auth（`jenkins_user` + `jenkins_api_token`），无论 `trigger_type` 是 `generic_webhook` 还是 `remote_api`

**Build URL 格式:**

| 格式 | URL 模式 |
|------|----------|
| `console` | `{base}/job/{path}/{number}/console` |
| `blueocean` | `{base}/blue/organizations/jenkins/{pipeline}/detail/{name}/{number}/pipeline` |

**form_data_template 占位符说明:**

| 占位符 | 说明 |
|--------|------|
| `{form_id}` | 表单 ID |
| `{form_title}` | 表单标题 |
| `{jenkins_job}` | Jenkins 任务路径 |
| `{username}` | 提交用户名 |
| `{request_params_json}` | 所有表单参数的 JSON 格式 |
| `{字段名}` | 任意表单字段（如 `{project}`, `{environment}`）|

**飞书审批配置 (`config/feishu_approval_config.yaml`):**

- `feishu_base_url`: 飞书 API 基础 URL（默认: "https://open.feishu.cn"）
- `feishu_timeout`: 请求超时时间（默认: 30 秒）
- `feishu_token_expire_buffer`: Token 刷新缓冲时间（默认: 300 秒，即过期前 5 分钟刷新）
- `apps`: 飞书应用配置（支持多应用）
  - 每个应用包含：
    - `app_id`: 飞书应用 ID（从飞书开发者控制台获取）
    - `app_secret`: 飞书应用密钥
    - `approval_code`: 默认审批定义码（UUID 格式）
    - `description`: 应用描述

**飞书审批配置示例:**

```yaml
feishu_base_url: "https://open.feishu.cn"
feishu_timeout: 30
feishu_token_expire_buffer: 300

apps:
  default:
    app_id: "cli_xxxxxxxxxx"
    app_secret: "your_app_secret_here"
    approval_code: "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
    description: "Default DevOps approval app"

  prod-release:
    app_id: "cli_yyyyyyyyyy"
    app_secret: "your_prod_app_secret"
    approval_code: "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY"
    description: "Production release approval"
```

**飞书审批 API 调用示例:**

```bash
# 发起审批单
curl -X POST http://localhost:8000/feishu-approval/create \
  -H "Content-Type: application/json" \
  -H "Cookie: session=xxx" \
  -d '{
    "app_name": "default",
    "feishu_user_id": "ce39af4f",
    "form_data": {
      "widget-id1": "发布版本: v1.0.0",
      "widget-id2": "发布环境: production"
    }
  }'

# 查询审批状态（按数据库 ID）
curl http://localhost:8000/feishu-approval/status/1 \
  -H "Cookie: session=xxx"

# 查询审批状态（按飞书实例码）
curl "http://localhost:8000/feishu-approval/status/instance/2B2ADE11-B477-4C84-A24E-706D3393B983?app_name=default" \
  -H "Cookie: session=xxx"
```

## 开发指南

### 日志系统

应用程序使用 Python 标准 logging 模块提供统一的日志管理：

**日志配置:**

- 日志级别可通过 `log_level` 环境变量控制 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- 支持控制台和文件输出
- 文件日志支持自动轮转
- 可配置日志格式和输出路径

**使用方式:**

```python
from app.utils.logger import get_logger

logger = get_logger(__name__)

logger.debug("Debug information")    # 开发调试信息
logger.info("Information message")   # 一般信息记录
logger.warning("Warning message")    # 警告信息
logger.error("Error message")        # 错误信息
logger.critical("Critical message")  # 严重错误
```

**安全注意事项:**

- 永远不要记录敏感信息 (密码、token、密钥)
- 对于调试信息，只记录必要的标识符，不记录完整内容
- 使用适当的日志级别，生产环境通常设置为 INFO 或 WARNING

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
- config/ 只放配置信息，逻辑代码不要放在 config 下面
- app/routers/ 接口定义，app/services 功能逻辑，app/models 模型定义
- main.py 是应用程序的入口点和路由注册，不放复杂的业务逻辑
- 对所有数据库模型使用 SQLModel
- 将灵活数据（标头、请求正文）存储为 JSON 列
- 对时间相关字段使用 Unix 时间戳

## 测试架构

### 测试工具栈

**测试框架:**

- **pytest** - 主要测试框架，支持丰富的插件生态
- **pytest-asyncio** - 异步测试支持
- **pytest-cov** - 测试覆盖率报告
- **faker** - 测试数据生成

**测试类型:**

- **单元测试** - 测试单个组件的功能
- **集成测试** - 测试 API 端点和组件交互
- **安全测试** - 测试认证和安全功能

**模拟和固件:**

- **unittest.mock** - Python 标准模拟库
- **SQLite** - 测试数据库（内存模式）
- **Redis Mock** - 模拟 Redis 连接

**测试环境:**

- **本地测试** - 直接在开发环境运行测试
- **Docker 测试** - 在容器化环境中运行测试（推荐）

### 测试项目结构

```text
tests/
├── conftest.py                 # 测试配置和共享固件
├── pytest.ini                 # pytest 配置文件
├── test_auth.py               # 认证 API 测试
├── test_models/               # 数据模型单元测试
│   ├── test_cmdb_trigger_reqlog.py   # CMDB Trigger 日志模型测试
│   └── test_feishu_bot_reqlog.py # 飞书机器人日志模型测试
├── test_services/             # 服务层单元测试
│   ├── test_redis_session.py # Redis 会话服务测试
│   ├── test_feishu_bot_service.py # 飞书机器人服务测试
│   ├── test_feishu_bot_webhook_mapping.py # 飞书机器人 Webhook 映射测试
│   └── test_login_config.py  # 登录配置测试
├── test_utils/               # 工具类测试
│   └── test_logger.py        # 日志工具测试
├── test_cmdb_trigger_integration.py  # CMDB Trigger API 集成测试
├── test_feishu_bot_integration.py # 飞书机器人 API 集成测试
├── test_security.py          # 安全和认证测试
├── Dockerfile.test          # Docker 测试镜像
├── docker-compose.test.yml  # Docker Compose 测试配置
├── run_tests.sh             # 本地测试运行脚本
├── run_tests_docker.sh      # Docker 测试运行脚本
└── TESTING.md               # 测试文档
```

### 测试类别和标记

应用程序使用 pytest 标记系统组织不同类型的测试：

**测试标记:**

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.security` - 安全测试
- `@pytest.mark.auth` - 认证测试
- `@pytest.mark.redis` - Redis 相关测试

**运行特定类别的测试:**

```bash
pytest tests/ -m unit          # 运行单元测试
pytest tests/ -m integration   # 运行集成测试
pytest tests/ -m security      # 运行安全测试
pytest tests/ -m auth          # 运行认证测试
pytest tests/ -m redis         # 运行 Redis 测试
```

### 测试环境配置

**测试数据库:**

- 使用 SQLite 内存数据库进行测试隔离
- 每个测试都有独立的数据库会话
- 自动清理测试数据，确保测试间无污染

**模拟外部依赖:**

- Redis 连接使用 Mock 对象
- HTTP 客户端请求使用 Mock 响应
- 外部 API 调用完全模拟

**环境变量:**

- `TESTING=1` - 启用测试模式
- `PYTHONPATH` - 自动设置项目路径

**Docker 测试环境:**

- **容器隔离**: 每次测试运行都使用全新的容器环境
- **依赖管理**: 自动启动 Redis 等测试依赖服务
- **结果持久化**: 测试结果和覆盖率报告保存到本地目录
- **环境一致性**: 与生产环境使用相同的 Docker 配置

### 运行测试

**快速开始:**

```bash
# 本地环境测试
pip install -r requirements.txt
./run_tests.sh

# Docker 环境测试（推荐）
./run_tests_docker.sh

# 或使用 pytest 直接运行
pytest tests/ -v
```

**Docker 测试命令:**

```bash
# 运行所有测试类别
./run_tests_docker.sh unit         # 单元测试
./run_tests_docker.sh integration  # 集成测试
./run_tests_docker.sh security     # 安全测试
./run_tests_docker.sh coverage     # 完整覆盖率测试

# 调试和开发
./run_tests_docker.sh shell        # 进入测试容器交互式环境
./run_tests_docker.sh clean        # 清理测试环境
```

**常用测试命令:**

```bash
# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html

# 运行特定测试文件
pytest tests/test_models/test_cmdb_trigger_reqlog.py -v

# 运行特定测试方法
pytest tests/test_models/test_cmdb_trigger_reqlog.py::TestCmdbTriggerReqLogModel::test_create_cmdb_trigger_reqlog -v

# 在失败时停止
pytest tests/ -x

# 显示详细输出
pytest tests/ -v -s
```

**并行测试:**

```bash
# 使用多进程运行测试（需要 pytest-xdist）
pytest tests/ -n auto
```

### 测试覆盖率

**覆盖率目标:**

- 单元测试覆盖率 > 80%
- 关键业务逻辑覆盖率 > 95%
- API 端点集成测试全覆盖

**查看覆盖率报告:**

```bash
# 终端报告
pytest tests/ --cov=app --cov-report=term-missing

# HTML 报告（生成 htmlcov/index.html）
pytest tests/ --cov=app --cov-report=html

# XML 报告（用于 CI/CD）
pytest tests/ --cov=app --cov-report=xml
```

### 编写测试指南

**测试文件命名:**

- 测试文件：`test_<module_name>.py`
- 测试类：`class Test<ClassName>:`
- 测试方法：`def test_<functionality>:`

**测试组织:**

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
class TestModelName:
    """Test description"""

    def test_specific_functionality(self, test_session):
        """Test specific functionality description"""
        # Arrange
        test_data = {...}

        # Act
        result = function_under_test(test_data)

        # Assert
        assert result.status == expected_status
```

**使用固件 (Fixtures):**

```python
def test_with_database(test_session):
    """Test using database session"""
    pass

def test_with_authentication(auth_headers):
    """Test with authentication headers"""
    pass

def test_async_endpoint(async_client):
    """Test async API endpoint"""
    pass
```

**模拟外部依赖:**

```python
@patch('app.services.external_service.make_request')
def test_external_api_call(mock_request):
    """Test external API integration"""
    mock_request.return_value = expected_response
    result = service_function()
    assert result == expected_result
```

### 持续集成测试

**预提交检查:**

```bash
# 运行测试套件
./run_tests.sh

# 检查代码格式
black --check app/ tests/

# 类型检查（如果启用）
mypy app/
```

**CI/CD 流水线:**

```yaml
# GitHub Actions 示例
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ --cov=app --cov-report=xml --junit-xml=junit.xml
```

### 测试最佳实践

**测试设计原则:**

- **AAA 模式**: Arrange（准备）、Act（执行）、Assert（断言）
- **测试隔离**: 每个测试都应该独立运行
- **清晰命名**: 测试名称应该描述测试场景
- **单一职责**: 每个测试只验证一个功能点

**数据处理:**

- 使用固件提供测试数据
- 避免硬编码测试值
- 使用 Faker 生成随机测试数据
- 清理测试后的数据状态

**异步测试:**

```python
@pytest.mark.asyncio
async def test_async_function(async_client):
    """Test async functionality"""
    response = await async_client.get("/api/endpoint")
    assert response.status_code == 200
```

**错误测试:**

```python
def test_error_handling():
    """Test error scenarios"""
    with pytest.raises(ExpectedException):
        function_that_should_raise_exception()
```

**参数化测试:**

```python
@pytest.mark.parametrize("input_value,expected", [
    ("valid_input", True),
    ("invalid_input", False),
])
def test_validation(input_value, expected):
    """Test multiple input scenarios"""
    assert validate_input(input_value) == expected
```

### 调试测试

**调试失败的测试:**

```bash
# 运行到第一个失败就停止
pytest tests/ -x

# 显示完整的错误追踪
pytest tests/ --tb=long

# 进入调试模式
pytest tests/ --pdb

# 显示打印输出
pytest tests/ -s
```

**日志调试:**

```python
import logging
logging.basicConfig(level=logging.DEBUG)

def test_with_logging():
    """Test with debug logging"""
    logger = logging.getLogger(__name__)
    logger.debug("Debug information for test")
```

## 重要说明

### Amis SDK embed 注意事项

- **不要覆盖 `env.confirm` 和 `env.alert`**：Amis SDK 通过 `preset.tsx` 自动注册了 React 渲染的 styled Modal 对话框（`amis-ui/components/Alert.tsx`）。在 `amis.embed()` 的选项中传入自定义 `confirm`/`alert` 函数会覆盖内置实现，导致退化为浏览器原生弹窗
- **`confirmText` 是 action/button 组件的属性，不是 form 组件的属性**：要在表单提交前弹出确认框，应在 form 的 `actions` 中自定义提交按钮并设置 `confirmText`，而不是在 form 节点上设置。支持 `${xxx}` 模板语法。`confirmTitle` 可设置对话框标题
- **表单提交确认的两种方式**：
  1. **简单确认**：在 submit 按钮上设置 `confirmText`（推荐，配置简单）
  2. **自定义确认弹窗**：使用 `actionType: "dialog"` 弹出自定义对话框，在对话框中通过 `actionType: "ajax"` 提交（适合需要展示参数摘要等复杂场景）

### 代码注释规范

- 所有代码内的注释必须使用英文
- 项目文档和配置说明可以使用中文
- 保持代码的国际化兼容性

### 测试注释规范

- 测试方法的文档字符串使用英文
- 测试描述要清晰说明测试目的
- 复杂测试逻辑要添加内联注释
