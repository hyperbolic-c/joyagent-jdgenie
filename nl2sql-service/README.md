# NL2SQL Service

独立的 NL2SQL 算法服务，从 genie-tool 中拆分出来，专注于 SQL 生成。

## 特性

- **接口完全兼容**：与现有 genie-tool 的 `/v1/tool/nl2sql` 接口完全兼容
- **LLM 配置灵活**：支持环境变量和请求级配置
- **独立部署**：可以单独扩缩容、独立监控
- **流式响应**：支持 SSE 流式输出思考过程

## 快速开始

### 本地开发

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置环境变量
```bash
export LLM_API_KEY=your_api_key
export LLM_BASE_URL=https://api.openai.com/v1
export NL2SQL_MODEL_NAME=gpt-4.1
```

3. 启动服务
```bash
python -m nl2sql.main
```

服务将在 http://localhost:1601 启动

### Docker 部署

```bash
docker-compose up -d
```

## API 接口

### NL2SQL 接口

**路径**: `POST /v1/tool/nl2sql`

**请求体**:
```json
{
  "requestId": "req-123",
  "query": "统计2024年每个月的销售额",
  "currentDateInfo": "2024-12-01",
  "modelCodeList": ["sales_order"],
  "schemaInfo": [
    {
      "modelCode": "sales_order",
      "schemaList": [
        {
          "columnId": "amount",
          "columnName": "金额",
          "dataType": "decimal",
          "columnComment": "订单金额"
        }
      ]
    }
  ],
  "stream": true,
  "dbType": "mysql",
  "llmConfig": {
    "model": "gpt-4.1",
    "apiKey": "optional-api-key",
    "temperature": 0.0
  }
}
```

**响应**:
- 流式模式：SSE 事件流
- 非流式模式：JSON 响应

### 健康检查

**路径**: `GET /health`

**响应**:
```json
{
  "status": "healthy",
  "service": "nl2sql-service"
}
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `LLM_API_KEY` | LLM API 密钥 | - |
| `LLM_BASE_URL` | LLM API 基础 URL | https://api.openai.com/v1 |
| `NL2SQL_MODEL_NAME` | SQL 生成模型 | gpt-4.1 |
| `REWRITE_MODEL_NAME` | 查询改写模型 | gpt-4.1 |
| `THINK_MODEL_NAME` | 思考分析模型 | gpt-4.1 |
| `PORT` | 服务端口 | 1601 |
| `LOG_LEVEL` | 日志级别 | INFO |

### 请求级配置

可以在请求体中通过 `llmConfig` 字段传递 LLM 配置，优先级高于环境变量。

## 与 genie-tool 的关系

- **nl2sql-service**：独立的 NL2SQL 服务
- **genie-tool**：保留其他功能（Code Interpreter、Deep Search 等）

切换方式：修改 Java 后端配置中的服务地址即可，无需修改代码。

```yaml
# application.yml
dataagent:
  agentUrl: http://nl2sql-service:1601  # 从 genie-tool:1601 修改
```
