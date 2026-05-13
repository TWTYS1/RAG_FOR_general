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
┌─────────────────────────────────────────────────────┐
│                     用户界面                          │
│           Streamlit Web UI  /  CLI 终端              │
└──────────────┬──────────────────┬───────────────────┘
               │                  │
    ┌──────────▼──────────┐  ┌───▼────────────────────┐
    │   离线索引流程       │  │   在线问答流程          │
    │                     │  │                        │
    │  docs/ (805 文件)    │  │  "useEffect 怎么用?"   │
    │    │                │  │    │                   │
    │    ▼                │  │    ▼                   │
    │  解析器路由          │  │  Embedding (Qwen3)     │
    │  PDF→pdfplumber     │  │  问题 → 1024维向量     │
    │  MD→markdown-it     │  │    │                   │
    │  HTML→BS4           │  │    ▼                   │
    │  DOCX→python-docx   │  │  ChromaDB 语义搜索     │
    │    │                │  │  Top-K=8 片段         │
    │    ▼                │  │    │                   │
    │  语义分块器          │  │    ▼                   │
    │  MD→标题感知        │  │  组装 Prompt           │
    │  段→句→递归回退     │  │  片段 + 系统指令       │
    │    │                │  │    │                   │
    │    ▼                │  │    ▼                   │
    │  Embedding (Qwen3)   │  │  DeepSeek API          │
    │  文本 → 1024维向量   │  │  生成可溯源回答         │
    │    │                │  │                        │
    │    ▼                │  │                        │
    │  ChromaDB 入库       │  │                        │
    │  chroma_data/       │  │                        │
    └─────────────────────┘  └────────────────────────┘
```

### 3.2 核心流程

**离线索引（一次性）**

```
805 文件 → FileTypeRouter → 解析去噪 → SemanticChunker → 分块
→ Embedder(GPU) → 1024维向量 → ChromaDB 持久化
→ 输出：4584 chunks，可检索
```

**在线问答（每次）**

```
用户问题 → Embedder(GPU) → 1024维向量 → ChromaDB.search(Top-K=8)
→ format_context(8片段) → Prompt 组装 → DeepSeek API
→ 回答（含来源标注 [1][2]...）
```

### 3.3 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 配置中心 | `src/config.py` | .env 读取、全局常量 |
| 解析器路由 | `src/parsers/router.py` | 按扩展名分发到 5 种解析器 |
| 语义分块 | `src/chunker.py` | Markdown 感知 + 递归回退 + Token 控制 |
| 向量化 | `src/embedder.py` | Qwen3-Embedding-0.6B 本地推理，GPU 加速 |
| 向量存储 | `src/chroma_store.py` | ChromaDB 读写、维度检测、metadata 过滤 |
| 检索 | `src/retrieve.py` | Query → Embedding → Search → Context 格式化 |
| 生成 | `src/generate.py` | Prompt 工程 → DeepSeek API → 答案后处理 |
| 索引管道 | `src/ingest.py` | 串联解析→分块→向量化→入库全流程 |
| Web UI | `src/app.py` | Streamlit 界面，聊天式交互 |
| CLI | `src/cli.py` | 终端问答，/index /filter /sources 命令 |

---

## 四、产出什么 — 交付物与效果

### 4.1 系统交付物

- **Streamlit Web 应用**：聊天式问答界面，支持文件类型筛选、来源溯源
- **CLI 命令行工具**：终端交互式问答
- **ChromaDB 向量库**：4584 个语义 chunks，覆盖 264 份文档
- **可执行测试脚本**：`scripts/test_pipeline.py` 端到端验证

### 4.2 回答质量要求

| 维度 | 目标 | 实现方式 |
|------|------|----------|
| 准确性 | 不编造信息 | System Prompt 约束 + low temperature (0.3) |
| 可溯源 | 每次回答标注来源 | `[1] 来源: file.md · [MD] · 第3页` |
| 完整性 | 多片段拼合 | Top-K=8，取多个相关段落 |
| 响应速度 | <5 秒 | GPU Embedding + DeepSeek API 快 |
| 安全 | 数据不出境（Embedding） | 本地模型，仅问题文本调 API |

### 4.3 效果示例

```
问：React 中 useEffect 怎么用？

答：useEffect 是一个 React Hook，用于将组件与外部系统同步 [1]。
它接受两个参数：一个包含副作用逻辑的函数，和一个依赖数组。
当依赖数组中的值变化时，effect 会重新执行 [1]。
返回 undefined [2]。

[1] 来源: useEffect.md · [MD]
[2] 来源: useEffect.md · [MD]
```

### 4.4 关键指标

| 指标 | 当前值 |
|------|--------|
| 索引文档数 | 264 文件 → 4584 chunks |
| Embedding 维度 | 1024 |
| 单次 Embedding | ~20ms (GPU) |
| 检索延迟 | <100ms |
| 生成延迟 | 2-5s (DeepSeek API) |
| 显存占用 | ~1.2GB (Qwen3-0.6B) |
| 磁盘占用 | ~80MB (向量库) + 1.2GB (模型) |

---

## 五、快速开始

### 环境要求

- Python 3.11+
- NVIDIA GPU + CUDA 12.8+（可选，CPU 也可跑）
- DeepSeek API Key

### 安装

```bash
# 1. 克隆项目
cd D:\vibecoding\project1

# 2. 创建虚拟环境 + 安装依赖
python -m venv rag-env
.\rag-env\Scripts\activate
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 4. 下载 Embedding 模型（约 1.2GB）
$env:HF_HUB_CACHE = "D:\vibecoding\models"
huggingface-cli download Qwen/Qwen3-Embedding-0.6B

# 5. 索引文档
python -c "from src.ingest import IngestPipeline; IngestPipeline().run()"
```

### 启动

```bash
# Web 界面
streamlit run src/app.py

# 或命令行
python src/cli.py
```

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
│   ├── chunker.py          # 语义分块器（Markdown 感知）
│   ├── chroma_store.py     # ChromaDB 存储层
│   ├── retrieve.py         # 检索 + Context 格式化
│   ├── generate.py         # Prompt 组装 + LLM 调用
│   ├── ingest.py           # 文档索引管道
│   ├── test_runner.py      # 测试框架
│   └── parsers/
│       ├── router.py       # 文件类型路由
│       ├── pdf_parser.py   # PDF → pdfplumber
│       ├── markdown_parser.py  # MD → markdown-it
│       ├── html_parser.py  # HTML → BeautifulSoup
│       ├── docx_parser.py  # DOCX → python-docx
│       └── text_parser.py  # TXT 纯文本
├── docs/                   # 文档库（按目录组织）
│   ├── ebooks/             # PDF 论文（通信/PASS定位等）
│   ├── my-notes/           # 个人笔记
│   ├── react-docs/         # React 官方文档（英文）
│   └── web-archive/        # 网页存档
├── scripts/
│   └── test_pipeline.py    # 端到端测试脚本
├── rag-env/                # Python 虚拟环境（gitignore）
├── chroma_data/            # ChromaDB 持久化数据（gitignore）
├── .env                    # API Key 等密钥（gitignore）
├── .env.example            # 环境变量模板
├── requirements.txt        # Python 依赖
├── check_env.py            # 环境检查工具
├── CLAUDE.md               # AI 编程助手指令
└── README.md               # 本文件
```
