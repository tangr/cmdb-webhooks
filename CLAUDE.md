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

```text
webhook-proxy/
├── app/                    # 主应用程序目录（后端API）
│   ├── dependencies.py     # 共享依赖（数据库会话管理、认证）
│   ├── main.py            # FastAPI应用程序入口点
│   ├── internal/          # 内部管理模块
│   │   └── admin.py       # 管理员路由和功能
│   ├── models/            # 数据模型
│   │   ├── cmdb_reqlog.py  # CMDB请求日志模型
│   │   └── feishu_reqlog.py # 飞书请求日志模型
│   ├── routers/           # API路由处理器
│   │   ├── auth.py        # 认证相关路由（JWT + Session + OIDC）
│   │   ├── cmdb.py        # CMDB日志路由
│   │   └── feishu.py      # 飞书Webhook代理路由
│   ├── services/          # 服务层模块
│   │   ├── feishu_service.py    # 飞书服务逻辑
│   │   ├── redis_session.py     # Redis会话管理服务
│   │   └── webhook_mapping.py   # Webhook映射服务
│   └── utils/             # 工具模块
│       ├── logger.py            # 日志工具
│       ├── template_filters.py  # Jinja2模板过滤器
│       └── webhook_security.py  # Webhook安全验证
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
- **请求日志记录**: 记录和管理来自 CMDB 和飞书等系统的 HTTP 请求/响应数据
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
  - `CmdbReqLog`: 存储来自 CMDB 系统的 HTTP 请求/响应数据
  - `FeishuReqLog`: 存储飞书 Webhook 代理的请求/响应数据
- 使用 JSON 列灵活存储标头和正文数据
- 时间戳存储为 Unix 时间戳

**Redis 会话存储:**

- 用于存储用户会话数据，支持过期时间管理
- 提供快速的会话查询和管理功能
- 支持集群部署时的会话共享
- 包含完整的会话生命周期管理（创建、读取、删除、清理）

### 关键数据模型

- **CmdbReqLog**: 存储来自 CMDB 系统的 HTTP 请求详细信息（方法、路径、标头、正文、状态等）
- **FeishuReqLog**: 存储飞书 Webhook 代理请求的详细信息（包括请求和响应数据）
- **User**: 用户认证和权限管理的用户实体（支持角色基础的访问控制）
- 所有模型遵循 SQLModel 模式，包含用于创建、更新和读取操作的独立类

### 关键服务组件

- **RedisSessionManager** (`app/services/redis_session.py`):

  - 提供完整的 Redis 会话管理功能
  - 支持会话创建、读取、删除和批量操作
  - 自动处理会话过期和清理
  - 包含管理员功能（查看所有会话、批量清理）

- **FeishuService** (`app/services/feishu_service.py`):

  - 处理飞书 Webhook 代理请求的核心业务逻辑
  - 包含安全验证和请求转发功能
  - 记录请求/响应日志

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
- `GET /auth/oidc/login` - OIDC 登录重定向
- `GET /auth/oidc/callback` - OIDC 回调处理
- `GET /auth/` - 根路径重定向

**CMDB 请求日志模块 (`/cmdb/*`)**

- `GET /cmdb/` - 列出所有日志（HTML 页面，需要认证）
- `POST /cmdb/` - 创建新日志条目（公开端点，用于接收 Webhook）
- `GET /cmdb/list` - 分页日志列表（需要认证）
- `GET /cmdb/{log_id}` - 获取特定日志（需要认证）
- `PUT /cmdb/{log_id}` - 更新日志条目（需要管理员权限）
- `DELETE /cmdb/{log_id}` - 删除日志条目（需要管理员权限）

**飞书 Webhook 模块 (`/feishu/*`)**

- `POST /feishu/webhook/proxy/{webhook_id}` - 飞书 Webhook 代理端点（按 ID）
- `POST /feishu/webhook/alias/{webhook_name}` - 飞书 Webhook 代理端点（按名称别名）
- `GET /feishu/logs` - 获取飞书 Webhook 日志列表
- `GET /feishu/logs/{log_id}` - 获取特定飞书 Webhook 日志

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
│   ├── test_cmdb_reqlog.py   # CMDB 日志模型测试
│   └── test_feishu_reqlog.py # 飞书日志模型测试
├── test_services/             # 服务层单元测试
│   ├── test_redis_session.py # Redis 会话服务测试
│   ├── test_feishu_service.py # 飞书服务测试
│   └── test_webhook_mapping.py # Webhook 映射测试
├── test_utils/               # 工具类测试
│   └── test_logger.py        # 日志工具测试
├── test_cmdb_integration.py  # CMDB API 集成测试
├── test_feishu_integration.py # 飞书 API 集成测试
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
pytest tests/test_models/test_cmdb_reqlog.py -v

# 运行特定测试方法
pytest tests/test_models/test_cmdb_reqlog.py::TestCmdbReqLogModel::test_create_cmdb_reqlog -v

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

### 代码注释规范

- 所有代码内的注释必须使用英文
- 项目文档和配置说明可以使用中文
- 保持代码的国际化兼容性

### 测试注释规范

- 测试方法的文档字符串使用英文
- 测试描述要清晰说明测试目的
- 复杂测试逻辑要添加内联注释
