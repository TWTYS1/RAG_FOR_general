# RAG 3GPP 标准文档分析平台

**面向通信研究者的 3GPP 智能检索系统。混合检索（语义 + BM25）+ 跨语言查询扩展 + 结构化差距分析模板，从 TDoc/CR/Meeting Notes 中挖掘标准空白、追踪剩余问题、发现专利机会。**

---

## 目录

- [一、项目定位](#一项目定位)
- [二、为什么要做 — 设计思路（AI PM 面试参考）](#二为什么要做--设计思路ai-pm-面试参考)
  - [2.1 问题定义](#21-问题定义)
  - [2.2 用户与场景](#22-用户与场景)
  - [2.3 竞品分析与差异化](#23-竞品分析与差异化)
  - [2.4 技术选型推演](#24-技术选型推演)
  - [2.5 关键设计决策](#25-关键设计决策)
- [三、怎么做 — 系统架构与执行流程](#三怎么做--系统架构与执行流程)
  - [3.1 宏观架构](#31-宏观架构)
  - [3.2 核心流程](#32-核心流程)
  - [3.3 模块职责](#33-模块职责)
- [四、产出什么 — 交付物与效果](#四产出什么--交付物与效果)
- [五、快速开始](#五快速开始)
- [六、技术栈](#六技术栈)
- [七、项目结构](#七项目结构)

---

## 一、项目定位

这是一个面向**技术团队的内部知识库问答系统**。用户上传技术文档（React 官方文档、通信论文、个人笔记等），系统通过语义理解找到最相关的内容，结合大模型生成准确、可溯源的回答。

**核心价值主张**：私密（本地 Embedding，数据不出境）、高效（GPU 加速）、可溯源（每条回答标注来源）。

---

## 二、为什么要做 — 设计思路（AI PM 面试参考）

### 2.1 问题定义

> 技术团队面临的核心矛盾：**文档太多（800+ 份），查不到，记不住。**

传统方案的问题：

| 方案 | 问题 |
|------|------|
| Ctrl+F / grep | 只能关键词匹配，"性能优化"搜不到"让 React 更快" |
| 手动整理 README | 维护成本随文档量指数增长 |
| 全文托管到 ChatGPT | 数据安全风险、token 成本、无法锁定来源 |
| 商业 RAG 产品 | 贵、定制差、技术文档场景优化不足 |

**核心需求**：一个能"理解"技术文档语义、找到相关内容、并给出可溯源回答的系统。

### 2.2 用户与场景

| 角色 | 场景 | 需求 |
|------|------|------|
| 开发者 | 查 API 用法 | "useEffect 怎么处理依赖数组？" |
| 研究生 | 文献综述 | "Pinching Antenna 定位精度如何？" |
| 新人 Onboarding | 快速了解技术栈 | "这个项目的架构是什么？" |
| PM / Tech Lead | 技术决策参考 | "React Server Components 的限制有哪些？" |

### 2.3 竞品分析与差异化

| 维度 | 本系统 | ChatGPT + 附件 | 企业 RAG 产品 |
|------|--------|---------------|--------------|
| 数据安全 | 高（Embedding 本地） | 低（全量上传） | 中 |
| 成本 | 仅 LLM API 费 | 订阅 + token | 高 |
| 定制程度 | 完全可控 | 低 | 中 |
| 部署复杂度 | 单机可跑 | 零部署 | 复杂 |
| 来源溯源 | 自动标注 | 需手动问 | 部分支持 |

**差异化**：本地 Embedding + 云端 LLM 的"半离线"架构，兼顾安全与智能。

### 2.4 技术选型推演

每层技术的选择逻辑：

```
Layer 1: 文档解析（Input Diversity）
  需求：PDF / MD / HTML / DOCX / TXT 都要能读
  评估：pdfplumber（表结构好）、markdown-it（性能好）、python-docx、BeautifulSoup
  结论：每种格式单一最佳方案，工厂模式路由

Layer 2: 文本分块（Chunking Quality）
  需求：保持语义完整性，避免检索碎片化
  评估：
    - 固定字数/token：简单但语义断裂
    - 段落分割：好于固定，但忽略文档结构
    - Markdown 标题感知：利用文档自身层级，最优
    - 语义相似度分割：效果好但慢，过度设计
  结论：Markdown 标题 → 段落 → 句子 → 逐级递归回退

Layer 3: 向量模型（Embedding Quality）
  需求：中文好、免费、本地跑
  评估：
    - OpenAI text-embedding-3：英文最强，但 API 费用、数据出境
    - BGE-M3：经典开源，1024 维
    - Qwen3-Embedding-0.6B：2025 新模型，中文 SOTA，多语言
  结论：Qwen3-Embedding-0.6B，1024 维，GPU 加速

Layer 4: 向量数据库（Storage & Retrieval）
  需求：本地持久化、支持 metadata 过滤、轻量
  评估：Pinecone（云）、Weaviate（重）、FAISS（无持久化）、ChromaDB
  结论：ChromaDB，开箱即用，本地 SQLite + 向量索引

Layer 5: 大语言模型（Generation）
  需求：中文好、便宜、OpenAI 兼容 API
  评估：OpenAI、Claude、通义千问、DeepSeek
  结论：DeepSeek（中文强、价格低、API 兼容、国内直接访问）
```

### 2.5 关键设计决策

| 决策 | 为什么 | 取舍 |
|------|--------|------|
| 本地 Embedding + 云端 LLM | 数据安全 + 智能上限 | 需 GPU / 稍慢 |
| 1024 维（非 2048） | 实际召回差异 <2%，存储减半 | 接受微小精度损失 |
| Token 重叠（overlap=100） | 防止关键信息切在边界 | 多占 ~20% 存储 |
| 分隔符递归回退 | 保证任何文档都能切 | 极端文档可能语义略差 |
| 维度不匹配自动检测 | 换模型时避免静默失败 | 需额外代码 |
| 按文件类型路由分块策略 | Markdown 有标题可借，PDF 没有 | 策略不一致但效果好 |

---

## 三、怎么做 — 系统架构与执行流程

### 3.1 宏观架构

```
                    用户界面
           Streamlit Web UI  /  CLI 终端
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
   离线索引流程                      在线问答流程
         │                               │
  docs/3gpp/ (TDoc/CR/Spec)      中文 query
         │                               │
  解析器路由 → DOCX/PDF               ▼
         │                    QueryProcessor
         ▼                    (中→英 + 术语扩展
  3GPP 元数据提取               + 4-variant生成)
  (TDoc/WG/Meeting)                  │
         │                    ┌───────┴───────┐
  SemanticChunker             ▼               ▼
  (heading-path感知        Dense          Sparse
   + 关键词加权副本)     Embedder          BM25
         │               (Qwen3)      (exact×1.5
         ▼                  │          boost×1.15)
  Embedding (Qwen3)     ChromaDB            │
  文本 → 1024维向量      Top-50         Top-50
         │                  │               │
         ▼                  └───┬───────────┘
  ChromaDB + BM25              ▼
  (双索引同步入库)         RRF 融合 (k=60)
                              │
                         Cross-Encoder
                           重排序
                              │
                         Top-8/15 片段
                              │
                         模板路由
                    (差距/问题/专利/通用)
                              │
                         DeepSeek API
                         生成回答 + 来源标注
```

### 3.2 核心流程

**离线索引（一次性）**

```
3GPP 文档 → FileTypeRouter → DOCX解析（TDoc/WG/Meeting提取）
→ SemanticChunker（heading-path + 关键词副本）→ Embedder(GPU/1024维)
→ ChromaDB 持久化 + BM25 内存索引 → 双索引就绪
```

**在线问答（每次）**

```
中文 query → QueryProcessor（术语扩展 + variant生成）
→ Hybrid Search: Dense(Top-50) + BM25(Top-50) → RRF融合
→ Cross-Encoder 重排序 → 模板路由 → DeepSeek 生成 → 回答+标注
```

### 3.3 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 配置中心 | `src/config.py` | .env 读取、全局常量 |
| 解析器路由 | `src/parsers/router.py` | 按扩展名分发到 5 种解析器 |
| DOCX 解析器 | `src/parsers/docx_parser.py` | 3GPP DOCX：TDoc/CR/Spec/WG/Meeting 提取 |
| 元数据提取 | `src/parsers/base.py` | 15 个 3GPP 正则 + 24 类关键词 |
| 语义分块 | `src/chunker.py` | heading-path 感知 + 3GPP 关键词加权副本 |
| 向量化 | `src/embedder.py` | Qwen3-Embedding-0.6B 本地推理，GPU 加速 |
| 向量存储 | `src/chroma_store.py` | ChromaDB + BM25 同步 + Hybrid Search (RRF) |
| 稀疏索引 | `src/bm25_index.py` | BM25 关键词检索 + exact/boost 加权 |
| 跨语言处理 | `src/query_processor.py` | 中→英术语映射 + 固定术语 + variant 生成 |
| 重排序 | `src/reranker.py` | Cross-Encoder (bge-reranker-v2-m3) 精排 |
| 结构化模板 | `src/templates.py` | 差距分析/剩余问题/专利机会 三大模板 |
| 检索 | `src/retrieve.py` | Hybrid → Rerank → Context（TDoc/WG 展示）|
| 生成 | `src/generate.py` | 3GPP System Prompt + 模板路由 → DeepSeek |
| 索引管道 | `src/ingest.py` | 解析→分块→向量化→双索引全流程 |
| Web UI | `src/app.py` | Streamlit，增强 3GPP 元数据展示 |
| CLI | `src/cli.py` | 终端问答，/index /filter /sources |
| 术语配置 | `config/` | 用户可编辑 fixed_terms.txt + term_map.txt |

---

## 四、产出什么 — 交付物与效果

### 4.1 系统交付物

- **Streamlit Web 应用**：聊天式问答，3GPP 元数据展示（TDoc/WG/Meeting/rrf_score）
- **CLI 命令行工具**：终端交互，支持 /index /filter /sources 命令
- **Hybrid 搜索引擎**：Dense (Qwen3) + Sparse (BM25) + RRF 融合 + Cross-Encoder 重排
- **3GPP 模板引擎**：自动路由差距分析 / 剩余问题 / 专利机会 三大模板
- **可配置术语表**：`config/` 下编辑即生效，无需改代码
- **评估套件**：5 维度 × 15+ 测试查询

### 4.2 回答质量保证

| 维度 | 目标 | 实现方式 |
|------|------|----------|
| 准确性 | 不编造信息 | System Prompt 约束 + low temperature (0.2) |
| 证据约束 | 每结论至少 1 个引用 | 模板强制要求 `[n]` 来源标注 |
| 术语精确 | TDoc/CR/Spec 编号匹配 | BM25 exact boost ×1.5 + fixed_terms 匹配 |
| 跨语言 | 中文问 → 英文 3GPP 查 | QueryProcessor 中→英 + variant 生成 |
| 结构化 | 按场景出不同格式 | 差距/问题/专利三大模板自动路由 |

### 4.3 效果示例

```
问：Rel-19 Case 3a 还有哪些 remaining issue？

答：**🔍 剩余问题追踪**

### Open Issue 清单
| # | Issue 描述 | TDoc | WG | 优先级 |
|---|-----------|------|----|--------|
| 1 | gNB-sided model 训练数据采集流程未定义 [1] | R1-2506173 | RAN1 | High |
| 2 | model monitoring 触发条件待明确 [2] | R1-2501410 | RAN1 | Medium |

### 详细分析
**Issue 1**: gNB-sided model 数据采集...
- **背景**: Rel-19 AI/ML positioning 定义了 Case 3a... [1]
- **阻塞原因**: OAM-based 和 RRC-based 方案未达成共识 [3]

[1] R1-2506173 Maintenance on AI-ML-based positioning.docx
[2] R1-2501410 Summary#1 AIML-positioning.docx
```

### 4.4 关键指标

| 指标 | 值 |
|------|-----|
| Embedding 维度 | 1024 |
| 混合检索初召回 | 50 (Dense) + 50 (BM25) |
| RRF 融合后 | Top-50 |
| 重排序后 | Top-8~15 |
| 单次 Embedding | ~20ms (GPU) |
| 检索延迟 | <200ms (含 BM25 + RRF) |
| 生成延迟 | 3-8s (DeepSeek API + 长模板) |
| 显存占用 | ~1.2GB (Qwen3-0.6B) + ~1.5GB (reranker) |

---

## 五、快速开始

### 环境要求

- Python 3.11+
- NVIDIA GPU + CUDA 12.8+（可选，CPU 也可跑但慢）
- DeepSeek API Key

### 安装

```bash
# 1. 环境准备
cd D:\vibecoding\project1
python -m venv rag-env
.\rag-env\Scripts\activate
pip install -r requirements.txt

# 2. 配置
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
# DOCS_DIR 默认指向 ./docs/3gpp

# 3. 下载模型
# Qwen3-Embedding-0.6B（约 1.2GB）
# bge-reranker-v2-m3（约 1.5GB，可选，关闭 RERANK_ENABLED=false 跳过）

# 4. 添加 3GPP 文档
# 将 TDoc/CR/Meeting Notes/Spec 放入对应目录:
#   docs/3gpp/tdocs/    — TDoc 文件 (.docx)
#   docs/3gpp/specs/    — TS/TR (.pdf/.docx)
#   docs/3gpp/meetings/ — Meeting Reports
#   docs/3gpp/cr/       — Change Requests

# 5. 索引
python -c "from src.ingest import IngestPipeline; IngestPipeline().run(clear=True)"
```

### 启动

```bash
# Web 界面
streamlit run src/app.py

# 或命令行
python src/cli.py
```

### 自定义术语

编辑 `config/fixed_terms.txt`（每行一个 3GPP 术语）和 `config/term_map.txt`（中文→英文映射），重启即生效。

---

## 六、技术栈

| 层 | 技术 | 说明 |
|---|------|------|
| LLM 生成 | DeepSeek (deepseek-chat) | OpenAI 兼容，中文 SOTA，低成本 |
| Embedding | Qwen3-Embedding-0.6B | 本地推理，1024维，GPU 加速 |
| 向量库 | ChromaDB | 本地持久化，metadata 过滤 |
| 文档解析 | pdfplumber / markdown-it / python-docx / BeautifulSoup4 | 5 格式全覆盖 |
| 分块策略 | Markdown 标题感知 + 递归分隔符回退 | 语义完整性优先 |
| UI | Streamlit + CLI | 双入口 |
| 环境 | PyTorch 2.11 + CUDA 12.8 | RTX 5060 8GB |

---

## 七、项目结构

```
project1/
├── src/
│   ├── app.py              # Streamlit Web UI
│   ├── cli.py              # CLI 交互问答
│   ├── config.py           # 集中配置（.env 驱动）
│   ├── embedder.py         # Qwen3-Embedding 封装
│   ├── chunker.py          # 语义分块器（heading-path + 关键词）
│   ├── chroma_store.py     # ChromaDB + Hybrid Search (RRF)
│   ├── bm25_index.py       # BM25 稀疏索引 + 加权
│   ├── reranker.py         # Cross-Encoder 重排序
│   ├── query_processor.py  # 跨语言查询扩展 + 术语映射
│   ├── templates.py        # 3GPP 结构化回答模板
│   ├── retrieve.py         # Hybrid 检索 → Rerank → Context
│   ├── generate.py         # Prompt 组装 + LLM 调用
│   ├── ingest.py           # 文档索引管道
│   └── parsers/
│       ├── router.py       # 文件类型路由
│       ├── base.py         # 3GPP 元数据提取（15 正则 + 24 关键词）
│       ├── docx_parser.py  # DOCX → python-docx（增强 3GPP）
│       ├── pdf_parser.py   # PDF → pdfplumber
│       ├── markdown_parser.py  # MD → markdown-it
│       ├── html_parser.py  # HTML → BeautifulSoup
│       └── text_parser.py  # TXT 纯文本
├── config/
│   ├── fixed_terms.txt     # 用户可编辑：3GPP 固定术语（每行一条）
│   └── term_map.txt        # 用户可编辑：中文→英文术语映射
├── docs/
│   └── 3gpp/               # 3GPP 文档库
│       ├── tdocs/           # TDoc (.docx)
│       ├── specs/           # TS/TR 技术规范
│       ├── meetings/        # 会议纪要
│       └── cr/              # Change Requests
├── scripts/
│   ├── test_pipeline.py    # 端到端测试
│   ├── test_chunker.py     # 分块测试
│   ├── test_query_processor.py  # 查询扩展测试
│   ├── test_hybrid.py      # 混合检索测试
│   └── test_3gpp_queries.py    # 5 维度评估查询
├── rag-env/                # 虚拟环境（gitignore）
├── chroma_data_3gpp/       # ChromaDB 持久化数据（gitignore）
├── .env                    # API Key（gitignore）
├── .env.example            # 环境变量模板
├── requirements.txt        # Python 依赖
├── CLAUDE.md               # AI 编程助手指令
└── README.md               # 本文件
```
