# 4. 表筛选阶段 (Table Filter)

**对应代码**: `table_column_filter.py::filter_table()`  
**Prompt 文件**: `table_rag.yaml`  
**用途**: 根据用户问题筛选相关的数据表（第一阶段：粗筛）

---

## 输入变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `query` | string | 用户查询问题 |
| `table_info` | string | 数据表信息列表（格式化后） |
| `user_info` | string | 用户信息 |
| `time_info` | string | 时间信息 |
| `model_code_list` | list | 表的编号列表 |

---

## 完整 Prompt 模板

```yaml
table_filter_prompt: |-
  # 角色
  你是一名精准的数据表匹配专家，擅长语义理解和业务逻辑推理。

  # 任务
  根据用户问题和数据表元信息，识别并输出与问题相关的数据表编号列表。

  # 判断标准
  1. **语义关联度**：分析问题中的实体、指标、条件、时间等元素，与表的以下维度进行匹配：
     - 表名与表描述
     - 字段名、字段描述及别名
     - 字段采样值

  2. **业务逻辑关联**：
     - 考虑间接但合理的业务关联
     - 识别问题隐含的数据需求
     - 考虑上下文信息中的用户背景和时间因素

  3. **全面性原则**：
     - 宁可多选也不漏选
     - 对模糊匹配的情况保持包容

  # 执行步骤
  1. 分解用户问题为核心语义单元
  2. 对每个数据表进行多维度匹配评估
  3. 确定最终相关表集合

  # 输出要求
  - 仅输出JSON格式的表编号列表，如[1, 2, 3]
  - 不包含任何解释或额外文本

  # 上下文信息
  - 用户信息：{{ user_info }}
  - 时间信息：{{ time_info }}

  # 用户问题
  {{ query }}

  # 数据表信息
  {{ table_info }}

  # 表的编号列表：
  {{table_id_list}}

  # 开始
  输出：
```

---

## 实际调用示例

```python
from jinja2 import Template
from genie_tool.util.prompt_util import get_prompt

table_rag_prompts = get_prompt("table_rag")
prompt = Template(table_rag_prompts["table_filter_prompt"]) \
    .render(
        model_code_list=model_code_list,
        table_info=table_info,
        user_info=self.user_info,
        time_info=self.time_info,
        query=self.query,
        memory_info=memory_info_str
    )
```

---

## 输出格式

```json
[1, 2, 3]
```

---

## 判断标准

### 1. 语义关联度
- 分析用户问题中的实体、指标、条件、时间等元素
- 与以下维度进行匹配：
  - 表名与表描述
  - 字段名、字段描述及别名
  - 字段采样值

### 2. 业务逻辑关联
- 考虑间接但合理的业务关联
- 识别问题隐含的数据需求
- 考虑上下文信息中的用户背景和时间因素

### 3. 全面性原则
- **宁可多选也不漏选**
- 对模糊匹配的情况保持包容

---

## 执行步骤

1. **分解用户问题** - 为核心语义单元
2. **多维度匹配评估** - 对每个数据表进行评估
3. **确定相关表集合** - 输出最终的相关表编号列表

---

## 两阶段过滤说明

表筛选是**两阶段过滤的第一阶段（粗筛）**：

```
┌─────────────────┐     ┌─────────────────┐
│  表筛选（粗筛）  │ ──► │ 字段筛选（精排） │
│  Table Filter   │     │  Column Filter  │
└─────────────────┘     └─────────────────┘
```

- **粗筛**：从大量表中快速筛选出可能相关的表
- **精排**：在粗筛结果中精细筛选相关字段

---

[上一页：SQL 生成阶段](./03_nl2sql.md) | [返回首页](./README.md) | [下一页：字段筛选阶段](./05_column_filter.md)
