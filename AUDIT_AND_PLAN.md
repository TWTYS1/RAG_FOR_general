# RAG 系统 3GPP 改造 — 审计报告与实施方案

## 一、现状审计

### 1.1 当前各模块能力矩阵

| 能力 | 现状 | 文件 | 3GPP 是否够用 |
|------|------|------|:---:|
| DOCX 解析 | 仅按 Word heading style 分段，不提取表格/编号/元数据 | parsers/docx_parser.py | ❌ |
| PDF 解析 | 按页提取，无结构 | parsers/pdf_parser.py | ❌ |
| MD 解析 | 标题感知，保留层级 | parsers/markdown_parser.py | ✅ |
| HTML 解析 | 去标签，丢失结构 | parsers/html_parser.py | ❌ |
| 分块 | MD标题感知 + 段落递归回退 | chunker.py | ⚠️ 需增强 |
| Embedding | Qwen3-0.6B, 1024维, GPU | embedder.py | ✅ |
| 向量存储 | ChromaDB 单集合, dense only | chroma_store.py | ⚠️ 需加 BM25 |
| 检索 | 单 query 向量, 无扩展/混合/重排 | retrieve.py | ❌ |
| 生成 | 通用技术助手 prompt | generate.py | ❌ |
| Metadata 过滤 | file_type 单字段 | chroma_store.py | ⚠️ 需扩展 |
| 跨语言 | 无 | 无 | ❌ |
| Rerank | 无 | 无 | ❌ |
| 证据约束 | 无 | 无 | ❌ |

### 1.2 核心问题清单

**P0 — 检索质量致命问题：**
1. DOCX 解析丢失 3GPP 结构 — TDoc编号/WG/meeting/CR编号全部未提取
2. 中文提问→英文文档无翻译层 — 跨语言语义桥断裂
3. 纯 dense search — 3GPP 固定术语（如"NRPPa"）语义模糊，需要 BM25 精确匹配
4. 无 reranking — top-8 直接喂 LLM，噪音大

**P1 — 回答质量严重问题：**
5. 无证据约束 — LLM 可能编造标准内容
6. 无 3GPP 结构化输出模板 — 无法用于"缺口挖掘"
7. 分块不保留 heading path — 丢了层级上下文

**P2 — 效果优化：**
8. 无关键词 boost — "remaining issue"等关键信号没被利用
9. 无 metadata filter 高级筛选 — 不能按 WG=RAN3 过滤
10. 无 query expansion — 中文"高层参数"没法找到"higher layer parameters"

### 1.3 现有 API 接口（不破坏）

```
Embedder.embed(texts) → list[list[float]]
Embedder.embed_single(text) → list[float]
ChromaStore.add(ids, embeddings, documents, metadatas)
ChromaStore.search(query_embedding, top_k, file_type=None) → list[dict]
Retriever.search(query, top_k, file_type=None) → list[dict]
Retriever.format_context(hits) → str
Generator.generate(query, context) → str
IngestPipeline.run(clear=False) → int
```

---

## 二、改造方案（分 9 步，小步实施）

### Step 2: 增强 DOCX 解析器（3GPP 结构提取）— 优先级 P0

**改动文件：** `src/parsers/docx_parser.py`, `src/parsers/base.py`

**新增能力：**
- 正则提取 TDoc 编号：`R[1-9]-[0-9]{6}` 等模式
- 正则提取 CR 编号：数字序列 + revision
- 提取 spec 编号：`TS 38.xxx`, `TR 38.xxx`
- 提取 WG：`RAN1`, `RAN2`, `RAN3`, `SA2`, etc.
- 提取 meeting：`RAN3#119bis` 等
- 提取公司/来源：文档头部 author/company/source 行
- 提取 agenda item 和 AI/ML 相关关键词
- 表格提取：用 python-docx 读取表格内容
- 每一段保留 heading path（heading stack）
- metadata 字段扩展：`tdoc`, `cr`, `spec`, `wg`, `meeting`, `company`, `title`, `section_path`

**策略：** 不重写 docx_parser，在现有 heading-style 分割基础上叠加 metadata 提取层。

### Step 3: 3GPP 感知分块策略 — 优先级 P0

**改动文件：** `src/chunker.py`, `src/config.py`

**新增能力：**
- 按 section/subsection heading 优先切分
- 对 DOCX 文档，按 heading path 层级切分
- 保留 heading_path 到每个 chunk metadata
- chunk_size 调整到 800 tokens（适配 3GPP 段落密度）
- overlap 150 tokens
- 关键词段落强化索引：解析时识别 "remaining issue", "open issue", "FFS", "way forward", "conclusion", "agreement" 等段落，生成额外 keyword-boosted chunk 副本

### Step 4: 跨语言查询处理 — 优先级 P0

**新增文件：** `src/query_processor.py`

**新增能力：**
- 中文 query 检测（Unicode range）
- 3GPP 术语映射字典
- 生成 4 种 variant query：
  a) 原文 query
  b) 英文翻译 query（基于术语映射）
  c) 术语扩展 query（同义词展开）
  d) 关键词 query（3GPP 固定术语列表）
- 示例：中文"高层参数" → "higher layer parameters", "RRC parameters", "LPP parameters", "NRPPa IE"

### Step 5: Hybrid Search — 优先级 P0

**改动文件：** `src/chroma_store.py`, `src/retrieve.py`
**新增文件：** `src/bm25_index.py`

**新增能力：**
- BM25 索引：内存中维护一个基于 rank-bm25 的稀疏索引
- 每次 add 时同步更新 BM25 索引
- search_hybrid() 方法：
  - dense: ChromaDB query (语义)
  - sparse: BM25 query (关键词/精确匹配)
  - 融合: RRF (Reciprocal Rank Fusion) 或加权求和
- TDoc/CR/spec 编号精确匹配加权
- remaining/open/FFS 关键词 boost
- Metadata filter 同时作用于 dense 和 sparse

### Step 6: Reranking — 优先级 P1

**新增文件：** `src/reranker.py`

**新增能力：**
- top_k 初召回到 50-100
- 多因子 rerank：
  a) 语义相关性 (dense score)
  b) 关键词命中率 (keyword score)
  c) metadata 匹配度
  d) 文档新旧（meeting 日期）
  e) 是否包含 conclusion/way forward/remaining issue
- 输出每条：relevance_score, match_reasons
- 可选：cross-encoder 精排（SentenceTransformer CrossEncoder）

### Step 7: 3GPP 答案生成模板 — 优先级 P1

**改动文件：** `src/generate.py`
**新增文件：** `src/templates.py`

**新增能力：**
- 3GPP 标准缺口挖掘模板
- 结构化字段输出：
  - 问题/缺口名称
  - WG/meeting/TDoc/CR
  - 当前状态
  - 相关公司
  - Way forward
  - Remaining issues
  - 接口影响
  - 专利切入点（标注"推断"）
  - 撞车风险
  - 证据摘录（英文原文）+ 来源
- 证据不足时明确输出
- 每个结论至少引用 1 个来源

### Step 8: 评测用例 — 优先级 P2

**新增文件：** `scripts/test_3gpp_queries.py`

5 个标准 query 的检索+生成 dry run。

### Step 9: README 更新 — 优先级 P2

在 README 中增加 3GPP 使用场景说明。

---

## 三、不改动的部分

- Embedder 保持不变（Qwen3-Embedding 多语言够用）
- ChromaDB 持久化不变
- 现有 CLI 和 Streamlit UI 不变
- 配置文件向后兼容
- 非 DOCX 的 parser 暂不改动（用户说 DOCX 是主力）

---

## 四、新增文件清单

| 文件 | 功能 |
|------|------|
| `src/query_processor.py` | 跨语言查询扩展 |
| `src/bm25_index.py` | BM25 稀疏索引 |
| `src/reranker.py` | 多因子重排序 |
| `src/templates.py` | 3GPP 回答模板 |
| `scripts/test_3gpp_queries.py` | 评测用例 |

## 五、修改文件清单

| 文件 | 改动 |
|------|------|
| `src/parsers/docx_parser.py` | 3GPP 元数据提取 + 表格 |
| `src/parsers/base.py` | Document metadata 字段扩展 |
| `src/chunker.py` | DOCX heading path + 关键词强化分块 |
| `src/config.py` | 新增配置项 |
| `src/retrieve.py` | Hybrid search + query expansion |
| `src/chroma_store.py` | search_hybrid 方法 |
| `src/generate.py` | 3GPP 模板支持 |
| `src/ingest.py` | 集成 BM25 索引更新 |
