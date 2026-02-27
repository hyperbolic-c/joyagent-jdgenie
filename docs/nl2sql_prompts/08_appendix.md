# 附录

---

## Prompt 调用流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NL2SQL Prompt 调用流程                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │   用户输入查询   │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────┐     ┌─────────────────┐                               │
│  │ 1. rewrite_prompt│     │ 4. table_filter_│                               │
│  │    查询改写      │     │    prompt 表筛选  │                               │
│  │                 │     │                 │                               │
│  │  输入: query    │     │  输入: query,   │                               │
│  │  输出: 改写后查询 │◄────│        table_info│                               │
│  │                 │     │  输出: [1,2,3]  │                               │
│  └────────┬────────┘     └─────────────────┘                               │
│           │                              ▲                                  │
│           │                              │                                  │
│           ▼                              │                                  │
│  ┌─────────────────┐     ┌─────────────────┐                               │
│  │ 2. extract_     │     │ 5. column_filter_│                              │
│  │    column_prompt│     │    prompt 字段筛选 │                              │
│  │    字段关键词提取 │     │                 │                              │
│  │                 │     │  输入: query,   │                              │
│  │  输入: query,   │     │        table_info│                              │
│  │        keywords │     │  输出: {related  │                              │
│  │  输出: [字段名列表]│────►│        Flag,    │                              │
│  │                 │     │        column    │                              │
│  └─────────────────┘     │        Indexes}  │                              │
│           │              └─────────────────┘                               │
│           │                              │                                  │
│           ▼                              │                                  │
│  ┌─────────────────┐                     │                                  │
│  │ 3. extract_cell_│                     │                                  │
│  │    prompt 单元格 │                     │                                  │
│  │    值提取       │                     │                                  │
│  │                 │                     │                                  │
│  │  输入: query,   │                     │                                  │
│  │        table_   │                     │                                  │
│  │        caption  │                     │                                  │
│  │  输出: [关键词列表]│─────────────────────┘                                  │
│  │                 │    (用于ES检索召回字段)                                    │
│  └─────────────────┘                                                        │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────┐     ┌─────────────────┐                               │
│  │ 6. think_prompt │     │ 7. nl2sql_prompt │                               │
│  │    思考分析      │     │    SQL生成       │                               │
│  │                 │     │                 │                               │
│  │  输入: query,   │────►│  输入: rewritten │                               │
│  │        m_schema │     │        _query,   │                               │
│  │        _formatted│     │        thinking_│                               │
│  │  输出: 思考过程  │     │        result,   │                               │
│  │    (流式输出)   │     │        m_schema_ │                               │
│  │                 │     │        formatted │                               │
│  └─────────────────┘     │  输出: 问题###sql │                               │
│                          │        @@@问题###sql│                            │
│                          └─────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 代码对应关系

| Prompt 文件 | 对应代码文件 | 对应函数 |
|-------------|--------------|----------|
| [01_rewrite.md](./01_rewrite.md) | `nl2sql.py` | `_text_to_rewrite()` |
| [02_think.md](./02_think.md) | `nl2sql.py` | `_collect_think_results()` |
| [03_nl2sql.md](./03_nl2sql.md) | `nl2sql.py` | `_nl2sql_convert()` |
| [04_table_filter.md](./04_table_filter.md) | `table_column_filter.py` | `filter_table()` |
| [05_column_filter.md](./05_column_filter.md) | `table_column_filter.py` | `_filter_single_table()` |
| [06_extract_column.md](./06_extract_column.md) | `table_rag.py` | `choose_schema()` |
| [07_extract_cell.md](./07_extract_cell.md) | `table_rag.py` | `choose_schema()` |

---

## 环境变量配置

### NL2SQL 相关模型配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `NL2SQL_MODEL_NAME` | gpt-4.1 | SQL 生成模型 |
| `REWRITE_MODEL_NAME` | gpt-4.1 | 查询改写模型 |
| `THINK_MODEL_NAME` | gpt-4.1 | 思考分析模型 |

### Table RAG 相关配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `TR_COLUMN_FILTER_MODEL_NAME` | gpt-4o-0806 | 字段筛选模型 |
| `TR_TABLE_FILTER_MODEL_NAME` | gpt-4o-0806 | 表筛选模型 |
| `TR_IS_FIRST_FILTER_TABLE` | true | 是否启用两阶段过滤 |
| `TR_TABLE_FILTER_BATCH_SIZE` | 5 | 批处理大小 |
| `TR_NEED_FILTER_TABLE_MIN_LENGTH` | 3 | 需要过滤的最小表数量 |
| `TR_SCHEMA_LIST_MAX_LENGTH` | 200 | schema 列表最大长度 |
| `TR_BUSINESS_PROMPT_MAX_LENGTH` | 3000 | 业务规则最大长度 |
| `TR_USE_PROMPT_MAX_LENGTH` | 500 | 使用说明最大长度 |

### Table RAG Agent 配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `TR_EXTRACT_SYS_WSD_MODEL_NAME` | gpt-4o-0806 | 关键词提取模型 |
| `TABLE_RAG_SCHEMA_LIST_MAX_LENGTH` | 200 | schema 列表最大长度 |
| `TABLE_RAG_BUSINESS_PROMPT_MAX_LENGTH` | 1500 | 业务规则最大长度 |
| `TABLE_RAG_USE_PROMPT_MAX_LENGTH` | 500 | 使用说明最大长度 |

---

## Prompt 文件位置

```
genie-tool/genie_tool/prompt/
├── nl2sql.yaml          # NL2SQL 相关 Prompt
├── table_rag.yaml       # Table RAG 相关 Prompt
├── plan_sop.yaml        # 计划 SOP Prompt
├── report.yaml          # 报告生成 Prompt
├── analysis.yaml        # 分析 Prompt
├── code_interpreter.yaml # 代码解释器 Prompt
└── deepsearch.yaml      # 深度搜索 Prompt
```

---

## 输出格式汇总

| 阶段 | 输出格式 | 示例 |
|------|----------|------|
| 查询重写 | 纯文本 | `张三的星座是什么的` |
| 思考分析 | 纯文本（3步骤） | `1. 拆解问题核心... 2. 匹配字段信息... 3. 推导回答逻辑...` |
| SQL 生成 | 特定格式 | `问题###sql@@@问题###sql` |
| 表筛选 | JSON 数组 | `[1, 2, 3]` |
| 字段筛选 | JSON 对象 | `{"relatedFlag": true, "columnIndexes": [1, 2, 3]}` |
| 字段关键词提取 | JSON 数组 | `["字段名1", "字段名2"]` |
| 单元格值提取 | JSON 数组 | `["关键词1", "关键词2"]` |

---

[上一页：单元格值提取](./07_extract_cell.md) | [返回首页](./README.md)
