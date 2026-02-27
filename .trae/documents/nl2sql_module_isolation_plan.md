# NL2SQL 算法模块独立化拆分规划

## 一、背景与目标

### 1.1 当前架构问题
当前 NL2SQL 功能内嵌在 `genie-tool` 服务中，与其他功能（如代码解释器、深度搜索等）耦合在一起，存在以下问题：
- **部署粒度粗**：无法独立扩缩容 NL2SQL 服务
- **资源竞争**：不同功能共享资源，可能相互影响
- **迭代受限**：算法迭代需要重新部署整个服务
- **配置复杂**：环境变量配置混杂，难以管理

### 1.2 拆分目标
将 NL2SQL 算法功能拆分为**独立的 HTTP 服务模块**，实现：
- 独立部署、独立扩缩容
- 通过 HTTP 请求体接收所有必要数据（表结构、LLM 配置等）
- 支持流式/非流式响应
- **保持与现有 Java 后端的接口兼容**（Java 后端暂不修改）

---

## 二、当前架构分析

### 2.1 现有数据流

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户请求                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Java 后端 (genie-backend) - 保持不变                                        │
│  ├── DataAgentController.chatQuery()                                        │
│  ├── DataAgentService.webChatQueryData()                                    │
│  └── Nl2SqlService.runNL2SQLSse() / runNL2SQLSync()                         │
│       ↓ HTTP POST/SSE                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Python 工具层 (genie-tool)                                                  │
│  ├── API 层: api/tool.py::post_nl2sql()                                     │
│  ├── 协议层: model/protocal.py::NL2SQLRequest                               │
│  ├── 核心算法: tool/nl2sql.py::NL2SQLAgent                                  │
│  │   ├── _text_to_rewrite()    # 查询改写                                   │
│  │   ├── ColumnFilterModule    # 表字段精排 (table_rag/)                    │
│  │   ├── _collect_think_results() # 思考分析 (流式)                         │
│  │   └── _nl2sql_convert()     # SQL 生成                                   │
│  ├── LLM 工具: util/llm_util.py::ask_llm()                                  │
│  └── Prompt 模板: prompt/nl2sql.yaml                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 当前请求/响应模型

**请求模型 (NL2SQLRequest)**：
```python
class NL2SQLRequest(BaseModel):
    request_id: str           # 请求 ID
    query: str                # 用户问题
    current_date_info: str    # 系统当前日期
    table_id_list: List[str]  # 表信息（modelCodeList）
    column_info: List[Dict]   # 字段信息（schemaInfo）
    stream: bool = True       # 是否流式响应
    dialect: str = "mysql"    # SQL 方言类型
```

**响应模型 (NL2SQLResult)**：
```java
public class NL2SQLResult {
    private Integer code;           // 状态码
    private String request_id;      // 请求 ID
    private String nl2sql_think;    // 思考过程
    private String status;          // 状态
    private List<NL2SQLData> data;  // SQL 结果列表
    private String err_msg;         // 错误信息
}
```

### 2.3 当前 LLM 配置（环境变量）

| 环境变量 | 说明 | 当前位置 |
|---------|------|---------|
| `NL2SQL_MODEL_NAME` | SQL 生成模型 | docker-compose.yml |
| `REWRITE_MODEL_NAME` | 查询改写模型 | docker-compose.yml |
| `THINK_MODEL_NAME` | 思考分析模型 | docker-compose.yml |
| `LLM_API_KEY` | LLM API 密钥 | docker-compose.yml |
| `LLM_BASE_URL` | LLM 基础 URL | docker-compose.yml |

---

## 三、目标架构设计

### 3.1 拆分后架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户请求                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Java 后端 (genie-backend) - 保持不变                                        │
│  └── Nl2SqlService → 调用独立 NL2SQL 服务 HTTP 接口                         │
│       （保持现有调用方式不变，仅修改服务地址）                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓ HTTP POST/SSE
┌─────────────────────────────────────────────────────────────────────────────┐
│  NL2SQL 独立服务 (nl2sql-service)                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  HTTP API 层                                                        │   │
│  │  ├── POST /v1/tool/nl2sql        # 兼容现有接口路径                  │   │
│  │  └── 保持与 genie-tool 完全兼容的请求/响应格式                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      ↓                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  核心算法引擎 (nl2sql/core/)                                        │   │
│  │  ├── agent.py        # NL2SQLAgent 主类                             │   │
│  │  ├── rewrite.py      # 查询改写模块                                 │   │
│  │  ├── think.py        # 思考分析模块                                 │   │
│  │  ├── sql_generator.py # SQL 生成模块                                │   │
│  │  └── schema_formatter.py # 表结构格式化                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      ↓                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LLM 客户端 (nl2sql/llm/)                                           │   │
│  │  └── client.py       # 支持请求级 LLM 配置的客户端                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      ↓                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  表字段筛选 (nl2sql/rag/)                                           │   │
│  │  └── column_filter.py # 表字段精排模块                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 关键改进点

1. **接口完全兼容**：保持 `/v1/tool/nl2sql` 接口路径和请求/响应格式不变，Java 后端无需修改
2. **LLM 配置通过请求体传递**：扩展请求模型，支持在请求体中传递 LLM 配置（同时兼容环境变量方式）
3. **独立服务部署**：可以单独扩缩容、独立监控
4. **清晰的模块边界**：算法逻辑与 API 层分离

---

## 四、详细设计方案

### 4.1 请求/响应模型（保持兼容 + 扩展）

#### 4.1.1 请求模型 (NL2SQLRequest) - 向后兼容

```python
class LLMConfig(BaseModel):
    """LLM 配置模型 - 支持每次请求独立配置"""
    model: Optional[str] = Field(default=None, description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API 密钥")
    base_url: Optional[str] = Field(default=None, description="API 基础 URL")
    temperature: float = Field(default=0.0)
    top_p: float = Field(default=0.0)
    max_tokens: Optional[int] = Field(default=None)


class NL2SQLRequest(BaseModel):
    """NL2SQL 请求模型 - 保持与现有接口兼容"""
    request_id: str = Field(alias="requestId")
    query: str = Field(description="用户问题")
    current_date_info: str = Field(alias="currentDateInfo")
    table_id_list: List[str] = Field(alias="modelCodeList", default=[])
    column_info: List[Dict] = Field(alias="schemaInfo", default=[])
    stream: bool = Field(default=True)
    dialect: str = Field(alias="dbType", default="mysql")
    
    # ========== 新增：可选的 LLM 配置（如不提供则使用环境变量）==========
    llm_config: Optional[LLMConfig] = Field(alias="llmConfig", default=None)
    """
    可选的 LLM 配置，支持在请求中指定：
    - model: 模型名称
    - api_key: API 密钥
    - base_url: API 基础 URL
    - temperature: 温度参数
    - top_p: top_p 参数
    
    如不提供，则使用环境变量配置（保持向后兼容）
    """
```

**兼容性说明**：
- 原有字段保持不变，Java 后端无需修改
- 新增 `llm_config` 字段为可选，不传则使用环境变量配置
- 支持逐步迁移到请求级配置

#### 4.1.2 响应模型 (NL2SQLResponse) - 保持不变

```python
class NL2SQLData(BaseModel):
    """单条 SQL 结果"""
    query: str = Field(description="子问题")
    nl2sql: str = Field(description="生成的 SQL")


class NL2SQLResponse(BaseModel):
    """NL2SQL 响应模型 - 与现有格式完全一致"""
    code: int = Field(description="状态码")
    request_id: str = Field(alias="requestId")
    status: str = Field(description="状态")
    nl2sql_think: Optional[str] = Field(alias="nl2sqlThink", default=None)
    data: List[NL2SQLData] = Field(default=[])
    err_msg: Optional[str] = Field(alias="errMsg", default=None)
```

### 4.2 API 接口设计

保持接口路径与现有 `genie-tool` 完全一致：

```python
@router.post("/nl2sql")
async def post_nl2sql(body: NL2SQLRequest):
    """
    NL2SQL 接口 - 与 genie-tool 完全兼容
    
    接口路径: /v1/tool/nl2sql
    请求/响应格式与现有 genie-tool 保持一致
    """
    pass
```

### 4.3 模块结构

```
nl2sql-service/                      # 独立服务根目录
├── nl2sql/                          # 主包
│   ├── __init__.py
│   ├── main.py                      # FastAPI 入口
│   ├── config.py                    # 服务配置
│   │
│   ├── api/                         # API 层
│   │   ├── __init__.py
│   │   ├── routes.py                # 路由定义（兼容现有接口）
│   │   └── middleware.py            # 中间件
│   │
│   ├── core/                        # 核心算法层
│   │   ├── __init__.py
│   │   ├── agent.py                 # NL2SQLAgent 主类
│   │   ├── rewrite.py               # 查询改写模块
│   │   ├── think.py                 # 思考分析模块
│   │   ├── sql_generator.py         # SQL 生成模块
│   │   └── schema_formatter.py      # 表结构格式化
│   │
│   ├── models/                      # 数据模型
│   │   ├── __init__.py
│   │   ├── request.py               # 请求模型（兼容 + 扩展）
│   │   └── response.py              # 响应模型（兼容）
│   │
│   ├── llm/                         # LLM 客户端
│   │   ├── __init__.py
│   │   ├── client.py                # LLM 调用客户端
│   │   └── config.py                # LLM 配置管理
│   │
│   ├── rag/                         # RAG 相关
│   │   ├── __init__.py
│   │   └── column_filter.py         # 表字段筛选
│   │
│   ├── prompts/                     # Prompt 模板
│   │   └── nl2sql.yaml              # NL2SQL 各阶段 Prompt
│   │
│   └── utils/                       # 工具函数
│       ├── __init__.py
│       ├── logging.py               # 日志工具
│       └── timer.py                 # 性能计时
│
├── tests/                           # 测试
│   ├── __init__.py
│   ├── test_api.py                  # API 测试
│   └── test_core.py                 # 核心算法测试
│
├── Dockerfile                       # 容器镜像
├── docker-compose.yml               # 本地开发编排
├── pyproject.toml                   # Python 依赖
├── requirements.txt                 # 依赖列表
└── README.md                        # 使用文档
```

### 4.4 核心类设计

#### 4.4.1 NL2SQLAgent 主类

```python
class NL2SQLAgent:
    """NL2SQL 核心代理类"""
    
    def __init__(
        self,
        queue: Optional[asyncio.Queue] = None,
        llm_config: Optional[LLMConfig] = None
    ):
        """
        Args:
            queue: 用于流式输出的队列
            llm_config: 请求级 LLM 配置（优先于环境变量）
        """
        self.queue = queue or asyncio.Queue()
        self.llm_config = llm_config
    
    async def run(self, body: NL2SQLRequest) -> Dict:
        """
        执行完整的 NL2SQL 流程
        
        流程：
        1. 查询改写 (Rewrite)
        2. 表字段筛选 (Column Filter)
        3. 思考分析 (Think) - 流式输出
        4. SQL 生成 (NL2SQL)
        """
        pass
```

#### 4.4.2 LLMClient 客户端（支持请求级配置）

```python
class LLMClient:
    """LLM 调用客户端 - 支持请求级配置覆盖环境变量"""
    
    def __init__(self, request_config: Optional[LLMConfig] = None):
        """
        Args:
            request_config: 请求级 LLM 配置，优先于环境变量
        """
        self.request_config = request_config
    
    def _get_config(self) -> Dict:
        """
        获取最终配置：请求配置 > 环境变量 > 默认值
        """
        config = {
            "model": os.getenv("NL2SQL_MODEL_NAME", "gpt-4.1"),
            "api_key": os.getenv("LLM_API_KEY"),
            "base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            "temperature": 0.0,
            "top_p": 0.0,
        }
        
        # 请求级配置覆盖环境变量
        if self.request_config:
            if self.request_config.model:
                config["model"] = self.request_config.model
            if self.request_config.api_key:
                config["api_key"] = self.request_config.api_key
            if self.request_config.base_url:
                config["base_url"] = self.request_config.base_url
            config["temperature"] = self.request_config.temperature
            config["top_p"] = self.request_config.top_p
        
        return config
    
    async def chat(
        self,
        messages: Union[str, List[Dict]],
        stream: bool = False,
        only_content: bool = True
    ) -> AsyncGenerator[Union[str, Any], None]:
        """调用 LLM"""
        config = self._get_config()
        # ... 调用 litellm
```

---

## 五、部署方案

### 5.1 Docker 部署

**Dockerfile**：
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY nl2sql/ ./nl2sql/
COPY prompts/ ./prompts/

# 暴露端口
EXPOSE 1601

# 启动命令
CMD ["python", "-m", "nl2sql.main"]
```

**docker-compose.yml**（独立服务）：
```yaml
version: '3.8'

services:
  nl2sql-service:
    build:
      context: ./nl2sql-service
      dockerfile: Dockerfile
    container_name: nl2sql-service
    ports:
      - "1601:1601"
    environment:
      # 默认 LLM 配置（可被请求覆盖）
      - NL2SQL_MODEL_NAME=${NL2SQL_MODEL_NAME:-gpt-4.1}
      - REWRITE_MODEL_NAME=${REWRITE_MODEL_NAME:-gpt-4.1}
      - THINK_MODEL_NAME=${THINK_MODEL_NAME:-gpt-4.1}
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_BASE_URL=${LLM_BASE_URL:-https://api.openai.com/v1}
      # 服务配置
      - LOG_LEVEL=INFO
      - PORT=1601
    volumes:
      - ./logs/nl2sql:/app/logs
    networks:
      - genie-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:1601/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 5.2 与现有 genie-tool 的关系

拆分后：
- **nl2sql-service**：独立运行，提供 NL2SQL 功能
- **genie-tool**：保留其他功能（Code Interpreter、Deep Search、Report、Auto Analysis）

**切换方式**：
仅需修改 Java 后端配置中的服务地址（从 `genie-tool:1601` 改为 `nl2sql-service:1601`），无需修改代码。

---

## 六、实施步骤

### 阶段一：准备工作（1 天）

1. **创建新服务目录结构**
   - 创建 `nl2sql-service/` 目录
   - 初始化 Python 项目结构

2. **提取核心代码**
   - 从 `genie-tool` 提取 NL2SQL 相关代码
   - 整理 Prompt 模板

### 阶段二：核心实现（3-4 天）

1. **实现数据模型**
   - 请求模型（兼容现有 + 扩展 LLM 配置）
   - 响应模型（保持兼容）

2. **实现 LLM 客户端**
   - 支持请求级配置覆盖环境变量
   - 支持流式/非流式调用

3. **实现核心算法模块**
   - NL2SQLAgent 主类
   - 查询改写、思考分析、SQL 生成模块
   - 表结构格式化

4. **实现 API 层**
   - `/v1/tool/nl2sql` 接口（与 genie-tool 兼容）
   - 流式/非流式响应

### 阶段三：测试验证（2 天）

1. **单元测试**
   - 各模块单元测试
   - LLM 配置合并逻辑测试

2. **兼容性测试**
   - 使用现有 Java 后端请求测试
   - 验证响应格式一致

3. **性能测试**
   - 并发性能测试
   - 与 genie-tool 对比

### 阶段四：部署上线（1 天）

1. **构建镜像**
   - 编写 Dockerfile
   - 构建镜像

2. **更新 docker-compose**
   - 添加 nl2sql-service 服务
   - 配置网络连接

3. **切换流量**
   - 修改 Java 后端服务地址配置
   - 验证功能正常

### 阶段五：清理工作（可选）

1. 从 `genie-tool` 移除 NL2SQL 代码（可选）
2. 更新文档

---

## 七、风险与应对

| 风险 | 影响 | 应对措施 |
|-----|------|---------|
| 接口不兼容 | 高 | 保持接口路径、请求/响应格式完全一致 |
| 性能下降 | 中 | 增加 HTTP 连接池，优化序列化 |
| LLM 配置安全 | 中 | API Key 支持从环境变量读取，请求中可选 |
| 服务稳定性 | 中 | 增加健康检查、重试机制 |

---

## 八、附录

### 8.1 与现有 genie-tool 的对比

| 特性 | 当前 genie-tool | 独立 nl2sql-service |
|-----|----------------|---------------------|
| 部署粒度 | 整个工具服务 | 仅 NL2SQL 功能 |
| LLM 配置 | 仅环境变量 | 环境变量 + 请求级配置 |
| 接口兼容性 | - | 完全兼容 |
| Java 后端修改 | - | 仅需修改服务地址配置 |
| 扩缩容 | 整体扩缩容 | 独立扩缩容 |

### 8.2 代码迁移映射

| 原文件 | 新位置 | 说明 |
|-------|-------|------|
| `genie_tool/tool/nl2sql.py` | `nl2sql/core/agent.py` | 核心算法 |
| `genie_tool/model/protocal.py::NL2SQLRequest` | `nl2sql/models/request.py` | 请求模型（扩展 LLM 配置） |
| `genie_tool/api/tool.py::post_nl2sql` | `nl2sql/api/routes.py` | API 路由（路径兼容） |
| `genie_tool/util/llm_util.py` | `nl2sql/llm/client.py` | LLM 客户端（增强配置） |
| `genie_tool/prompt/nl2sql.yaml` | `nl2sql/prompts/nl2sql.yaml` | Prompt 模板 |
| `genie_tool/tool/table_rag/table_column_filter.py` | `nl2sql/rag/column_filter.py` | 字段筛选 |

### 8.3 Java 后端配置变更

仅需修改 `application.yml` 中的服务地址：

```yaml
# 修改前
dataagent:
  agentUrl: http://genie-tool:1601

# 修改后
dataagent:
  agentUrl: http://nl2sql-service:1601
```

**无需修改 Java 代码！**

---

## 九、总结

本规划方案专注于将 NL2SQL 算法功能从 `genie-tool` 中拆分出来，形成独立的 Python 服务，同时保持与现有 Java 后端的完全兼容。

核心特点：
1. **接口完全兼容**：Java 后端无需修改代码，仅需修改服务地址配置
2. **LLM 配置灵活**：支持环境变量（向后兼容）和请求级配置（新特性）
3. **独立部署**：可以单独扩缩容、独立监控
4. **平滑迁移**：支持逐步切换，风险可控

通过此拆分，可以实现更灵活的算法迭代和更细粒度的资源管理，同时保持系统的稳定性。
