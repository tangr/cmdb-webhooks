# 测试指南

本文档描述如何运行和使用 webhook-proxy 项目的测试套件。

## 快速开始

运行所有测试：

```bash
# 使测试运行器可执行（一次性操作）
chmod +x run_tests.sh

# 运行所有测试
./run_tests.sh
```

## 测试类别

测试套件使用 pytest 标记组织为几个类别：

- **单元测试** (`-m unit`): 隔离测试单个组件
- **集成测试** (`-m integration`): 测试 API 端点和组件交互
- **安全测试** (`-m security`): 测试安全和认证机制
- **认证测试** (`-m auth`): 测试特定的认证功能
- **Redis 测试** (`-m redis`): 测试依赖 Redis 的功能

## 运行特定测试类别

```bash
# 仅单元测试
pytest tests/ -m unit

# 仅集成测试
pytest tests/ -m integration

# 仅安全测试
pytest tests/ -m security

# 认证相关测试
pytest tests/ -m auth

# Redis 依赖测试
pytest tests/ -m redis
```

## 运行单个测试文件

```bash
# 测试特定模型
pytest tests/test_models/test_cmdb_reqlog.py
pytest tests/test_models/test_feishu_bot_reqlog.py

# 测试特定服务
pytest tests/test_services/test_redis_session.py
pytest tests/test_services/test_feishu_bot_service.py
pytest tests/test_services/test_webhook_mapping.py

# 测试 API 端点
pytest tests/test_auth.py
pytest tests/test_cmdb_integration.py
pytest tests/test_feishu_bot_integration.py

# 测试工具类
pytest tests/test_utils/test_logger.py
pytest tests/test_security.py
```

## 测试覆盖率

生成覆盖率报告：

```bash
# 终端覆盖率报告
pytest tests/ --cov=app --cov-report=term-missing

# HTML 覆盖率报告（在 htmlcov/index.html 中打开）
pytest tests/ --cov=app --cov-report=html

# XML 覆盖率报告（用于 CI/CD）
pytest tests/ --cov=app --cov-report=xml
```

## 测试配置

测试套件使用以下配置文件：

- **pytest.ini**: 主 pytest 配置，包含标记、覆盖率设置
- **tests/conftest.py**: 共享测试固件和设置
- **run_tests.sh**: 测试运行器脚本，包含环境设置

## 测试数据库

测试默认使用 SQLite 内存数据库，在 `conftest.py` 中配置：

- **测试数据库 URL**: `sqlite:///./test.db`
- **Redis 数据库**: 使用数据库 14（与生产环境不同）
- **自动清理**: 每次测试后清理测试数据

## 环境变量

以下环境变量影响测试：

- `TESTING=1`: 测试运行器自动设置以启用测试模式
- `PYTHONPATH`: 自动设置为包含项目根目录

## 持续集成

对于 CI/CD 流水线，使用：

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试并生成 XML 输出
pytest tests/ --cov=app --cov-report=xml --junit-xml=junit.xml
```

## 测试结构

```text
tests/
├── conftest.py              # 共享固件和配置
├── test_auth.py            # 认证 API 测试（现有）
├── test_models/            # 模型单元测试
│   ├── test_cmdb_reqlog.py
│   └── test__feishu_bot_reqlog.py
├── test_services/          # 服务单元测试
│   ├── test_redis_session.py
│   ├── test_feishu_bot_service.py
│   └── test_webhook_mapping.py
├── test_utils/            # 工具类单元测试
│   └── test_logger.py
├── test_cmdb_integration.py    # CMDB API 集成测试
├── test_feishu_bot_integration.py  # 飞书 API 集成测试
└── test_security.py           # 安全和认证测试
```

## 编写新测试

### 测试文件命名

- 单元测试：`test_<module_name>.py`
- 集成测试：`test_<feature>_integration.py`
- 放在适当的子目录中（`test_models/`、`test_services/` 等）

### 测试类命名

```python
@pytest.mark.unit  # 或 @pytest.mark.integration
class TestModelName:
    """测试描述"""
    
    def test_specific_functionality(self):
        """测试特定功能描述"""
        pass
```

### 使用固件

`conftest.py` 中可用的常用固件：

```python
def test_database_operation(test_session):
    """使用测试数据库会话"""
    pass

def test_api_endpoint(async_client, auth_headers):
    """使用带认证的异步 HTTP 客户端"""
    pass

def test_with_mock_redis(mock_redis):
    """使用模拟的 Redis 连接"""
    pass
```

### 标记测试

```python
@pytest.mark.unit
def test_unit_functionality():
    pass

@pytest.mark.integration  
def test_api_endpoint():
    pass

@pytest.mark.security
def test_authentication():
    pass

@pytest.mark.redis
def test_redis_functionality():
    pass
```

## 调试测试

运行测试时增加详细度和详细输出：

```bash
# 详细输出和完整回溯
pytest tests/ -v --tb=long

# 在第一次失败时停止
pytest tests/ -x

# 运行特定测试并输出
pytest tests/test_models/test_cmdb_reqlog.py::TestCmdbReqLogModel::test_create_cmdb_reqlog -v -s

# 失败时运行 pdb 调试器
pytest tests/ --pdb
```

## 性能测试

对于性能敏感的测试：

```bash
# 运行并显示时间信息
pytest tests/ --durations=10

# 性能分析慢速测试
pytest tests/ --profile
```

## Docker 测试

项目支持在 Docker 容器中运行测试，以获得更好的隔离性和跨环境一致性。

### Docker 测试设置

**测试特定文件：**

- `Dockerfile.test` - 专用于测试的 Dockerfile
- `docker-compose.test.yml` - 测试的 Docker Compose 配置
- `run_tests_docker.sh` - Docker 测试运行器脚本

### 在 Docker 中运行测试

**快速开始：**

```bash
# 使脚本可执行（一次性操作）
chmod +x run_tests_docker.sh

# 在 Docker 中运行所有测试
./run_tests_docker.sh

# 运行特定测试类别
./run_tests_docker.sh unit
./run_tests_docker.sh integration
./run_tests_docker.sh security
```

**可用的 Docker 命令：**

```bash
# 所有测试类别
./run_tests_docker.sh unit         # 仅单元测试
./run_tests_docker.sh integration  # 仅集成测试
./run_tests_docker.sh security     # 仅安全测试
./run_tests_docker.sh auth         # 仅认证测试
./run_tests_docker.sh redis        # 仅 Redis 测试

# 特殊命令
./run_tests_docker.sh coverage     # 所有测试及覆盖率
./run_tests_docker.sh shell        # 测试容器中的交互式 shell
./run_tests_docker.sh clean        # 清理测试环境
```

### Docker 测试环境

**测试容器：**

- **test-runner**: 运行 pytest 及所有依赖的主容器
- **test-redis**: 集成测试的 Redis 容器（可选）

**测试隔离：**

- 每次测试运行使用新鲜的容器
- SQLite 内存数据库用于数据隔离
- 单独的 Redis 数据库（DB 14）用于测试隔离
- 测试完成后自动清理

**环境变量：**

- `TESTING=1` - 启用测试模式
- `DATABASE_URL=sqlite:///./test.db` - 测试数据库
- `REDIS_HOST=test-redis` - 测试 Redis 实例

### Docker 测试结果

测试结果和覆盖率报告自动保存到本地目录：

```bash
# 查看测试结果
open htmlcov/index.html              # 覆盖率 HTML 报告
cat test-results/junit.xml           # JUnit XML 报告
cat test-results/coverage.xml        # 覆盖率 XML 报告
```

**结果目录：**

- `htmlcov/` - HTML 覆盖率报告
- `test-results/` - 用于 CI/CD 的 XML 报告

### Docker 开发工作流

**开发测试：**

```bash
# 开发过程中运行测试
./run_tests_docker.sh unit

# 在容器中调试
./run_tests_docker.sh shell
# 然后在容器内：
pytest tests/test_models/ -v -s
```

**CI/CD 集成：**

```bash
# 在 CI/CD 流水线中
./run_tests_docker.sh coverage

# 解析 XML 结果
cat test-results/junit.xml
cat test-results/coverage.xml
```

### Docker Compose 覆盖

对于自定义测试环境，创建 `docker-compose.test.override.yml`：

```yaml
services:
  test-runner:
    environment:
      - CUSTOM_ENV_VAR=value
    volumes:
      - ./custom-config:/app/custom-config
```

### Docker 测试的优势

**一致性：**

- 开发、CI/CD 和生产环境相同
- 消除"在我机器上可以运行"的问题
- 一致的 Python 版本和依赖

**隔离性：**

- 与宿主系统完全隔离
- 每次测试运行的干净环境
- 不受宿主服务干扰

**可扩展性：**

- 易于在并行容器中运行测试
- 与 CI/CD 系统简单集成
- 一致的测试时间和资源使用

## 故障排除

### 常见问题

1. **导入错误**: 确保 `PYTHONPATH` 包含项目根目录
2. **数据库错误**: 检查测试数据库权限和清理
3. **Redis 错误**: 验证测试配置中的 Redis 连接设置
4. **异步错误**: 对异步测试函数使用 `pytest-asyncio`
5. **Docker 错误**: 确保 Docker 正在运行且可访问

### Docker 特定问题

1. **权限错误**: 检查 Docker 守护进程权限
2. **端口冲突**: 确保测试端口（6380）可用
3. **构建失败**: 使用 `./run_tests_docker.sh clean` 清理 Docker 缓存
4. **卷问题**: 检查 Docker 卷权限

### 测试隔离

如果测试相互干扰：

```bash
# 本地测试
pytest tests/ -n auto  # 需要 pytest-xdist
pytest tests/ --forked  # 需要 pytest-forked

# Docker 测试（自动隔离）
./run_tests_docker.sh unit
```
