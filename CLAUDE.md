# 3GPP AI 定位 RAG 工作约定

## 项目定位
3GPP AIML-based Positioning 标准文档的语义检索与分析平台。
用户是标准研究员，需要从 TDoc / CR / 会议纪要 / TR 规范中挖掘论文思路和专利机会。

## 风险评估

| 风险 | 行为 | 示例 |
|------|------|------|
| 🟢 低 | 直接执行 | src/ 编辑, docs/ 加文件, 运行索引/审计, pip install 到 rag-env |
| 🟡 中 | 告知后执行 | 改 .env, 改 CLAUDE.md, 改 requirements.txt |
| 🔴 高 | 必须征得同意 | 项目外操作, git push --force, 系统级安装 |

## 项目边界
- 所有产物在 `D:\vibecoding\project1\` 内
- 虚拟环境 `rag-env/`，ChromaDB 数据 `chroma_data_3gpp/`
- .env 不提交 Git

## 技术栈

| 层 | 方案 |
|-----|------|
| LLM | DeepSeek (deepseek-chat) |
| Embedding | Qwen3-Embedding-0.6B (1024-dim, GPU) |
| 向量库 | ChromaDB 持久化 + BM25Okapi 稀疏索引 |
| 检索 | Dense + BM25 RRF 融合 (k=60) |
| 重排序 | BAAI/bge-reranker-v2-m3 Cross-Encoder |
| 文档解析 | python-docx / pdfplumber / markdown-it-py |
| 生成 | 3GPP 模板路由 (gap / issue / patent) |
| UI | CLI 直接调用 → 可启动 Streamlit |

## 文档库 (docs/3gpp/)
- `cr/` — Change Request 文档
- `meetings/` — RAN1/RAN2/RAN3 会议纪要
- `specs/` — TR 38.843 等规范段落
- `tdocs/` — 各公司技术贡献文档
- **审计**: `IngestPipeline(docs_dir='docs/3gpp').run(audit_only=True)` → ingest_audit_report.json/md
- **入库**: `IngestPipeline(docs_dir='docs/3gpp').run(incremental=True)` — 只处理新/改/删文件，断点续传

## 用户工作流
种子 TDoc/会议 → 检索摸底 → 定向扩词 → 精准下载 → 喂回验证 → 锁定缺口 → 再扩相邻

## 检索提问模式
当用户问专利/差距/问题相关的 3GPP 问题时：
1. 运行 `Retriever().search(query)` 获取混合检索结果
2. 用 `Retriever().format_context(hits)` 格式化为 evidence
3. 如果用户问专利/差距/未解决问题，启用对应模板（detect_template）
4. 通过 `Generator().generate(query, context, template)` 调 DeepSeek 生成分析
5. 输出包含：证据引用、差距识别、专利机会建议

## 专利分析方法
- 先定位哪些技术点被多份 TDoc 反复提及但未进入规范正文
- 检查 CR 中标记为 "remaining issue" "open issue" "FFS" 的内容
- 交叉对比会议纪要中的未达成共识点与 TR 中的空白章节
- 结论必须标注来源编号 [1] [2]，编不出东西时明确说"当前文档库未覆盖"
