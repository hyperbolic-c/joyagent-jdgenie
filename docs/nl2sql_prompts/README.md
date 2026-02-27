# NL2SQL 算法 LLM 提示词文档

本文档整理了 NL2SQL 系统中每一步输入给 LLM 的提示词（Prompt）。

---

## 目录结构

```
docs/nl2sql_prompts/
├── README.md                 # 本文档 - 总览和导航
├── 01_rewrite.md            # 查询重写阶段
├── 02_think.md              # 思考分析阶段
├── 03_nl2sql.md             # SQL 生成阶段
├── 04_table_filter.md       # 表筛选阶段
├── 05_column_filter.md      # 字段筛选阶段
├── 06_extract_column.md     # 字段关键词提取
├── 07_extract_cell.md       # 单元格值提取
└── 08_appendix.md           # 附录（流程图、环境变量）
```

---

## 各阶段说明

### 核心流程（按执行顺序）

| 序号 | 阶段 | 文件 | 说明 |
|------|------|------|------|
| 1 | 查询重写 | [01_rewrite.md](./01_rewrite.md) | 将用户原始查询优化为更清晰的表达方式 |
| 2 | 字段关键词提取 | [06_extract_column.md](./06_extract_column.md) | 生成用于向量检索的字段关键词 |
| 3 | 单元格值提取 | [07_extract_cell.md](./07_extract_cell.md) | 提取用于 ES 检索的单元格关键词 |
| 4 | 表筛选 | [04_table_filter.md](./04_table_filter.md) | 粗筛：选择相关的数据表 |
| 5 | 字段筛选 | [05_column_filter.md](./05_column_filter.md) | 精排：选择相关的字段 |
| 6 | 思考分析 | [02_think.md](./02_think.md) | 流式输出问题拆解和逻辑分析 |
| 7 | SQL 生成 | [03_nl2sql.md](./03_nl2sql.md) | 生成最终的 SQL 语句 |

### 附录

| 文件 | 内容 |
|------|------|
| [08_appendix.md](./08_appendix.md) | Prompt 调用流程图、环境变量配置 |

---

## 快速导航

### 按功能分类

#### 预处理阶段
- [查询重写](./01_rewrite.md) - 消除歧义、补充业务规则

#### RAG 检索阶段
- [字段关键词提取](./06_extract_column.md) - 用于 Qdrant 向量检索
- [单元格值提取](./07_extract_cell.md) - 用于 Elasticsearch 检索

#### 筛选阶段
- [表筛选](./04_table_filter.md) - 两阶段过滤的第一阶段（粗筛）
- [字段筛选](./05_column_filter.md) - 两阶段过滤的第二阶段（精排）

#### 生成阶段
- [思考分析](./02_think.md) - 流式展示分析过程
- [SQL 生成](./03_nl2sql.md) - 生成最终 SQL

---

## 环境变量配置

快速参考：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `NL2SQL_MODEL_NAME` | gpt-4.1 | SQL 生成模型 |
| `REWRITE_MODEL_NAME` | gpt-4.1 | 查询改写模型 |
| `THINK_MODEL_NAME` | gpt-4.1 | 思考分析模型 |
| `TR_COLUMN_FILTER_MODEL_NAME` | gpt-4o-0806 | 字段筛选模型 |
| `TR_TABLE_FILTER_MODEL_NAME` | gpt-4o-0806 | 表筛选模型 |

更多配置详见 [附录](./08_appendix.md)。

---

## 代码对应关系

| Prompt 文件 | 对应代码文件 | 对应函数 |
|-------------|--------------|----------|
| 01_rewrite.md | `nl2sql.py` | `_text_to_rewrite()` |
| 02_think.md | `nl2sql.py` | `_collect_think_results()` |
| 03_nl2sql.md | `nl2sql.py` | `_nl2sql_convert()` |
| 04_table_filter.md | `table_column_filter.py` | `filter_table()` |
| 05_column_filter.md | `table_column_filter.py` | `_filter_single_table()` |
| 06_extract_column.md | `table_rag.py` | `choose_schema()` |
| 07_extract_cell.md | `table_rag.py` | `choose_schema()` |

---

*文档生成时间: 2026-02-27*
