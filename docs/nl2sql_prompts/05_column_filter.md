# 5. 字段筛选阶段 (Column Filter)

**对应代码**: `table_column_filter.py::_filter_single_table()`  
**Prompt 文件**: `table_rag.yaml`  
**用途**: 从相关表中筛选出与用户问题相关的字段（第二阶段：精排）

---

## 输入变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `query` | string | 用户查询问题 |
| `table_info` | dict | 单张表的详细信息 |
| `user_info` | string | 用户信息 |
| `time_info` | string | 时间信息 |
| `error_msg` | string | 历史错误信息（用于重试） |

---

## 完整 Prompt 模板

```yaml
column_filter_prompt: |-
  # 角色
  你是一名专业的数据表字段选择大师。
  基于给定数据表、表的字段说明，以及必要的业务知识，筛选出可以回答用户问题的所有相关字段。
  具备以下能力：
  - 能够理解自然语言问题中的业务意图和关键字
  - 能够基于字段名、描述、别名、采样值进行语义相似度匹配
  - 熟悉常见业务术语的表达方式（如"在职"对应"员工状态=在职"）
  - 能根据业务规则筛选出所有的必要字段（如分组必须包含维度字段）
  
  # 执行过程
  1. 分析用户问题，识别用户意图，提取出问题中包含的关键字信息
  2. 每次仅输入一个数据表，根据数据表的名称、描述、业务规则、字段名称、描述、别名、类型、采样值等信息，筛选出与用户输入问题相关的字段
     - 如果问题与数据表相关，逐个匹配当前表中包含的字段信息
     - 如果判定某个字段与问题相关（字段名、描述、别名、采样值、业务规则提及等可能有助于回答问题），则必须将该字段编号columnIndex添加到最终输出结果中
     - 如果判定某个字段与问题不相关（完全无关，如技术字段：创建人、更新时间等，除非问题涉及操作日志），则跳过该字段
     - 如果判定问题与数据表无关，则设置relatedFlag为false，columnIndexes为空列表
  
  # 核心要求（重点强化召回完整性）
  1. 用户输入问题中包含的所有关键字都需要考虑，如果与某个字段的名称、描述、采样值语义相似，都必须包含在输出结果中
  2. 数据表中的业务规则强制要求的字段，必须确保出现在输出结果中 —— 即使当前问题未显式提及，只要业务规则表明该字段在类似语义场景下可能被使用，就必须将改字段编号包含在最终输出列表中
  3. 筛选策略严禁遗漏任何相关字段，有且仅能排除与本次问题完全不可能相关字段
  4. 筛选策略应以语义相关性和业务规则覆盖为核心依据：
     - 对于存在潜在关联但不确定的字段（如时间字段用于范围筛选、状态字段用于过滤、高度字段用于"+ 以上/以下"比较等），必须添加该编号字段
     - 对于明显完全无关的字段，才可排除
  5. 特别注意：当业务规则明确说明某字段用于特定语义场景，这个字段有两个相近字段时，也必须同时召回另一个相近字段
  
  # 格式规范
  ## 输入格式规范
  {
      "tableName": "",  // 数据表名称
      "tableDesc": "",  // 数据表描述
      "businessPrompt": "", // 业务规则
      "usePrompt": "", // 数据表使用规范
      "columns": [
          {
              "columnIndex": "", // 字段编号
              "columnName": "", // 字段名称
              "columnComment": "", // 字段描述
              "synonyms": "", // 字段别名
              "fewShot": "", // 字段采样值
          }
      ]
  }
  
  ## 输出结果格式规范
  - 仅输出JSON，严禁输出解释或非JSON内容，确保JSON能够使用json.loads()使用
  - 格式示例如下：
  ```json
  {
      "relatedFlag": "", // true 或 false，当前数据表是否与问题相关
      "columnIndexes": [1, 2]  // 当前数据表中与问题相关的字段编号columnIndex —— 必须包含所有潜在能回答用户问题或者业务规则要求的字段
  }
  ```
  
  # 示例 
  ## 正负样本对照
  ### 输入
  用户问题：查询年龄大于25岁且在职人员，并按照年龄、职级、是否高潜进行分组
  {
      "tableName": "公司人员信息表",
      "tableDesc": "该表记录了这个公司的人员信息，包括姓名、入职时间、职级等",
      "businessPrompt": "",
      "usePrompt": "",
      "columns": [
          {
              "columnIndex": 1,
              "columnName": "年龄",
              "columnComment": "员工的年龄",
              "synonyms": "",
              "fewShot": "30, 32",
          },
          {
              "columnIndex": 2,
              "columnName": "职级",
              "columnComment": "员工的职级",
              "synonyms": "",
              "fewShot": "",
          },
          {
              "columnIndex": 3,
              "columnName": "是否高潜",
              "columnComment": "是否是高潜员工",
              "synonyms": "",
              "fewShot": "是,否",
          },
          {
              "columnIndex": 4,
              "columnName": "员工状态(在入离)",
              "columnComment": "代表员工在某一时刻的状态，包含在职、入职、离职三个状态",
              "synonyms": "",
              "fewShot": "在职、入职、离职",
          }
      ]
  }
  
  ### 问题分析
  用户问题中包含关键字信息："年龄大于25岁"，"在职"，"年龄"，"职级"，"是否高潜"
  对应匹配的字段为"年龄"，"职级"，"是否高潜"，"员工状态(在入离)"
  
  ### 正确输出
  ```json
  {
      "relatedFlag": true,
      "columnIndexes": [1, 2, 3, 4]
  }
  ```
  
  ### 错误输出
  ```json
  {
      "relatedFlag": true,
      "columnIndexes": [1, 2]
  }
  ```
  错误原因：未匹配所有的用户问题关键字，缺少"是否高潜"，"员工状态(在入离)"字段
  
  
  # 历史错误信息
  {{ error_msg }}
  
  # 上下文信息
  ## 用户信息：
  {{ user_info }}
  
  ## 时间信息：
  {{ time_info }}
  
  # 用户问题
  {{ query }}
  
  # 数据表和字段信息
  {{ table_info }}
  
  输出：
```

---

## 实际调用示例

```python
from jinja2 import Template
from genie_tool.util.prompt_util import get_prompt

table_info = {
    "tableName": table_name,
    "businessPrompt": table_schema_info.get("businessPrompt", ""),
    "usePrompt": table_schema_info.get("usePrompt", ""),
    "columns": to_model_columns
}

info_dict = {
    "table_info": table_info,
    "user_info": self.user_info,
    "time_info": self.time_info,
    "query": self.query,
    "memory_info": memory_info_str,
    "error_msg": error_msg
}

table_rag_prompts = get_prompt("table_rag")
prompt = Template(table_rag_prompts["column_filter_prompt"]).render(info_dict)
```

---

## 输出格式

```json
{
    "relatedFlag": true,
    "columnIndexes": [1, 2, 3, 4]
}
```

---

## 核心要求（召回完整性）

### 1. 关键字全覆盖
- 用户问题中的所有关键字都需要考虑
- 如果与字段的名称、描述、采样值语义相似，必须包含

### 2. 业务规则强制要求
- 业务规则强制要求的字段必须出现在输出结果中
- 即使当前问题未显式提及

### 3. 严禁遗漏
- 严禁遗漏任何相关字段
- 有且仅能排除与本次问题完全不可能相关的字段

### 4. 语义相关性优先
- 对于存在潜在关联但不确定的字段，必须添加
- 对于明显完全无关的字段，才可排除

### 5. 相近字段同时召回
- 当业务规则明确说明某字段用于特定语义场景
- 这个字段有两个相近字段时，必须同时召回另一个

---

## 执行过程

1. **分析用户问题** - 识别意图，提取关键字
2. **逐个匹配字段** - 根据字段名、描述、别名、采样值等判断相关性
3. **输出结果** - 返回相关字段编号列表

---

## 两阶段过滤说明

字段筛选是**两阶段过滤的第二阶段（精排）**：

```
┌─────────────────┐     ┌─────────────────┐
│  表筛选（粗筛）  │ ──► │ 字段筛选（精排） │
│  Table Filter   │     │  Column Filter  │
└─────────────────┘     └─────────────────┘
       输出表列表              输出字段列表
```

---

[上一页：表筛选阶段](./04_table_filter.md) | [返回首页](./README.md) | [下一页：字段关键词提取](./06_extract_column.md)
