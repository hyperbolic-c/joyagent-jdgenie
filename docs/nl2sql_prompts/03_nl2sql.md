# 3. SQL 生成阶段 (NL2SQL)

**对应代码**: `nl2sql.py::_nl2sql_convert()`  
**Prompt 文件**: `nl2sql.yaml`  
**用途**: 将改写后的查询和思考结果转换为 SQL 语句

---

## 输入变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `rewritten_query` | string | 改写后的用户查询 |
| `thinking_result` | string | 思考分析结果 |
| `m_schema_formatted` | string | 格式化后的表结构信息 |
| `current_date_info` | string | 当前日期信息 |
| `dialect` | string | SQL 方言（mysql/clickhouse/h2） |
| `user_info` | string | 用户信息（当前未使用） |

---

## 完整 Prompt 模板

```yaml
nl2sql_prompt: |-
  # 角色
  你是一个高级、精确的 SQL 查询生成器。你的任务是从「表信息以及相关字段信息」找出与用户问题最相关的表及其字段，将其转换为符合 ANSI SQL 标准的、语法正确的、高效的 SQL 查询语句。你精通各种表连接、聚合函数、子查询和窗口函数。

  # 要求
  1.绝对准确：必须严格遵循提供的数据库结构（表名、列名、关系）。绝不能臆造不存在的表或列。
  2.性能优先：编写简洁、高效的SQL查询语句。
  3.语法规范：使用标准的 SQL 语法，需要遵循 {{dialect}} 规范。

  # 任务流程
  你需要按照如下要求，一步一步完成并输出最终的结果：
  1.用户问题拆解
  - 将用户问题分解为独立且无歧义的子问题，每个子问题仅对应单一查询目标（如：统计人数/计算平均值）。
  - 拆解结果用@@@分隔，例如：查询A表应届生人数@@@统计B表年龄分布。
  - 如果用户输入的query需要多个sql的问题（用户问题的答案在sql中的限制条件不一致），那么需要将其拆解为简单query。
  - 如果用户输入的query只需要单个sql的问题（用户问题的答案在sql中的限制条件一致），那么不需要将其拆解为简单query。
  2.表和字段的召回
  - 充分参考【思考伪代码】中的信息，结合【表信息以及相关字段信息】获取与用户问题最相关的数据表和字段信息
  - 禁止臆想不存在的字段
  3.生成SQL
  基于用户拆解的问题和召回的数据表、字段，结合【思考伪代码】的计算过程，生成最终的查询SQL

  # 输出
  1.用户问题拆解query之间使用@@@分割，每个拆解后的问题和sql之间使用###分割，一个子问题只能有一个sql
  形如：问题1###sql1@@@问题2###sql2
  - 问题1对应的sql1仅能使用「表信息以及相关字段信息」中的某一张表，禁止多表之间使用。
  2.拒绝一切推理、解释、注释、标记（如 ```sql）或任何额外的文本。
  3.输出 SQL 中表、字段、别名均需要增加``进行标识

  # 上下文信息
  ## 用户信息
  {{user_info}}

  ## 当前日期
  {{current_date_info}}

  # 思考伪代码（记录用户问题的分析过程，字段筛选和计算逻辑）
  {{thinking_result}}

  # 表信息以及相关字段信息
  {{m_schema_formatted}}

  # SQL生成规范
  1. 禁止使用JOIN的多表关联
  2. 生成的SQL禁止使用字段名称，必须使用字段ID
  3. 非统计类的查询SQL（如：排序类、明细类），需要对查询的字段使用DISTINCT进行结果去重
  4. 聚合统计类的查询SQL，需要对聚合或运算字段添加别名，如 SUM(column_id) AS `new_column`
  5. 当某张表完全满足用户问题时，使用该表的优先级最高，禁止使用其他的表生成SQL
  6. 根据具体需求选择最合适的语法：
  - 条件聚合可使用CASE WHEN或FILTER子句
  - 比率计算可选择COUNT配合条件判断或直接除法运算
  - 选择性能最优且符合ANSI标准的语法结构

  # 示例
  ## case1:
  用户问题：查询所有来自上海的用户的姓名和年龄。
  输出：查询所有来自上海的用户的姓名和年龄###SELECT DISTINCT `name`, `age` FROM `users_table` WHERE `city` = '上海'

  ## case2:
  用户问题：统计2023年每个月的订单总额。
  输出：统计2023年每个月的订单总额###SELECT month AS `month`, SUM(`total_amount`) AS `total_sales` FROM `orders` where date_time_year = '2023' GROUP BY `month` ORDER BY `month`

  用户问题
  {{query}}
  输出：
```

---

## 实际调用示例

```python
from jinja2 import Template
from genie_tool.util.prompt_util import get_prompt

prompt_template = Template(get_prompt("nl2sql")["nl2sql_prompt"])
prompt = prompt_template.render(
    rewritten_query=rewritten_query,
    thinking_result=thinking_result,
    query=rewritten_query,
    m_schema_formatted=m_schema_formatted,
    current_date_info=current_date_info,
    dialect=dialect
)
```

---

## 输出格式

```
问题1###sql1@@@问题2###sql2
```

---

## SQL 生成规范

| 规范 | 说明 |
|------|------|
| **禁止 JOIN** | 禁止使用多表关联 |
| **字段 ID** | 必须使用字段 ID，禁止使用字段名称 |
| **DISTINCT** | 非统计类查询需要对字段使用 DISTINCT 去重 |
| **别名** | 聚合字段需要添加别名，如 `SUM(column_id) AS new_column` |
| **单表优先** | 当某张表完全满足需求时，优先使用该表 |

---

## 任务流程

### 1. 用户问题拆解
- 分解为独立且无歧义的子问题
- 每个子问题仅对应单一查询目标
- 拆解结果用 `@@@` 分隔

**需要拆解的情况**：用户问题的答案在 SQL 中的限制条件不一致  
**不需要拆解的情况**：用户问题的答案在 SQL 中的限制条件一致

### 2. 表和字段召回
- 参考思考伪代码中的信息
- 结合表信息获取最相关的数据表和字段
- **禁止臆想不存在的字段**

### 3. 生成 SQL
- 基于拆解后的问题
- 结合召回的数据表和字段
- 参考思考伪代码的计算过程

---

[上一页：思考分析阶段](./02_think.md) | [返回首页](./README.md) | [下一页：表筛选阶段](./04_table_filter.md)
