"""3GPP 结构化回答模板：差距分析/剩余问题/专利机会 + 证据约束"""

# ── 模板触发词 ─────────────────────────────────

TEMPLATE_TRIGGERS = {
    "gap": [
        "gap", "差距", "缺失", "未定义", "不完整", "矛盾", "冲突",
        "兼容性", "互操作", "enhancement", "missing", "contradiction",
        "incompatible", "undefined",
    ],
    "issue": [
        "remaining issue", "open issue", "未解决", "待解决", "遗留问题",
        "未决", "pending", "outstanding", "todo", "further study",
        "需要进一步研究", "后续版本", "revisit",
    ],
    "patent": [
        "patent", "专利", "创新", "方案", "机会", "空窗", "空白",
        "novel", "invention", "opportunity", "未覆盖", "技术空白",
        "标准空白", "specification gap",
    ],
}

# ── 系统指令 ───────────────────────────────────

SYSTEM_PROMPT_3GPP = """你是 3GPP 标准分析专家，面向中国通信研究者，辅助标准差距挖掘与专利机会发现。

## 核心原则
1. **严格基于证据**：每个结论必须至少引用 1 条文档片段，标注来源编号如 [1]、[2]
2. **不能编造**：如果文档不足以支撑判断，明确说"当前文档库未覆盖此问题"
3. **中文回答**：使用中文，但 3GPP 术语保留英文原文（TDoc、CR、TS/TR、WG、RAN1 等）
4. **结构化输出**：按模板组织内容，便于快速定位关键信息
5. **多源交叉验证**：如果多个来源对同一问题有不同表述，指出差异

## 3GPP 基础知识
- TDoc: 3GPP 技术文档，编号格式 R1~R8-XXXXXX
- CR (Change Request): 标准修改请求
- TS (Technical Specification) / TR (Technical Report): 技术规范/报告
- WG (Working Group): RAN1~R4, SA1~SA6, CT1~CT6
- Release: Rel-15/16/17/18/19
- Meeting: 如 RAN1#119bis 格式
- LS (Liaison Statement): 联络函

## 输出要求
- 关键 3GPP 编号（TDoc、CR、Spec）必须在正文中显式标出
- 使用 [1] [2] 标注引用，每个引用对应一条检索到的文档片段
- 如果涉及 TDoc，列出编号及对应的 WG/Meeting 信息
- 建议部分可适度推测，但必须标注为"推测"或"建议"并说明依据"""

# ── 模板定义 ───────────────────────────────────

def build_gap_prompt(query: str, context: str) -> str:
    return f"""## 任务：3GPP 标准差距分析

请分析以下标准文档，识别**规范空白、技术矛盾、兼容性问题**。

{context}

## 分析要求
1. **现有规范覆盖**：当前标准已定义了哪些相关内容？列出关键 TS/TR 编号及要点
2. **规范空白**：哪些场景/技术点在现有标准中缺失或不完整？
3. **矛盾点**：不同 WG 或不同 Release 之间是否存在矛盾或冲突？
4. **影响评估**：这些差距对实际部署的影响程度？按高/中/低分级
5. **建议方向**：可能的补全路径（新 CR、新 SI/WI 提案、后续 Release 规划）

## 输出格式
### 现有覆盖
- (TS/TR 编号): 要点简述 [来源]

### 规范空白
- 空白点 1: 描述 + 影响的场景 [来源]

### 矛盾/冲突
- 如有则列出，无则说明"未发现明显矛盾"

### 影响评估表
| 空白/矛盾 | 影响程度 | 涉及 WG | 紧迫度 |
|-----------|---------|---------|--------|

### 建议
- 可操作的补全建议

## Query
{query}"""


def build_issue_prompt(query: str, context: str) -> str:
    return f"""## 任务：3GPP 剩余问题追踪

请梳理以下文档中提及的**未解决问题、待办事项、后续研究方向**。

{context}

## 分析要求
1. **问题清单**：列出所有 open/remaining issue，标注涉及的 TDoc/CR 编号
2. **讨论历史**：简要回顾该问题的讨论脉络（哪个 Meeting 提出、各公司立场）
3. **阻塞原因**：为什么尚未解决？（技术难度/缺乏仿真数据/等待 LS 答复/公司间分歧）
4. **优先级评估**：按对标准进展的影响判断高/中/低优先级
5. **预计解决路径**：下一次相关会议可能如何推进？

## 输出格式
### Open Issue 清单
| # | Issue 描述 | TDoc | WG | Meeting | 优先级 |
|---|-----------|------|----|---------|--------|

### 详细分析
对每个 High/Medium 优先级 issue：
- **背景**:
- **当前状态**:
- **阻塞原因**:
- **预测**: 下一步可能动作
- **来源**: [1][2]...

## Query
{query}"""


def build_patent_prompt(query: str, context: str) -> str:
    return f"""## 任务：3GPP 专利机会发现

请基于以下标准文档，识别**潜在可专利的技术空白点**。

{context}

## 分析要求
1. **技术空白点**：标准尚未覆盖但有明确需求的技术方向
2. **现有方案局限**：当前规范中提到的方案存在哪些不足？
3. **创新方向建议**：可能的技术解决路径（可基于通信领域常识推测，但须标注为推测）
4. **专利可行性评估**：从新颖性、实用性、标准必要性三个维度评估
5. **相关 IPR 风险提示**：如果已知相关专利声明，请指出

## 输出格式
### 技术空白点
| # | 空白方向 | 涉及标准章节 | 潜在价值 |
|---|---------|------------|---------|

### 详细分析（每个有潜力的方向）
- **现状**: 标准当前定义 [来源]
- **不足**: 存在什么问题
- **创新建议** (推测): 可能的技术方案
- **专利可行性**: 新颖性/实用性/标准必要性评分（1-5）

### 风险提示
- 已知相关公司在此方向的活跃度/声明

## Query
{query}"""


def build_general_prompt(query: str, context: str) -> str:
    """通用 3GPP 问答（非特定分析模板）"""
    return f"""## Context（检索到的文档片段）

{context}

## Query
{query}

请基于上述文档片段回答。要求：
- 关键 3GPP 编号（TDoc/CR/Spec）显式标出
- 结论标注来源 [1][2]...
- 无法确认的内容明确说明"""

# ── 路由函数 ───────────────────────────────────

def detect_template(query: str) -> str:
    """根据 query 关键词自动选择模板类型"""
    q = query.lower()
    scores = {"gap": 0, "issue": 0, "patent": 0}
    for tpl, keywords in TEMPLATE_TRIGGERS.items():
        for kw in keywords:
            if kw in q:
                scores[tpl] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def build_prompt(query: str, context: str, template: str | None = None) -> str:
    """根据模板类型构建 prompt"""
    tpl = template or detect_template(query)
    if tpl == "gap":
        return build_gap_prompt(query, context)
    elif tpl == "issue":
        return build_issue_prompt(query, context)
    elif tpl == "patent":
        return build_patent_prompt(query, context)
    else:
        return build_general_prompt(query, context)
