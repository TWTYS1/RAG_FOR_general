# RAG 项目工作约定

## 风险评估机制

执行任何操作前，按以下标准判定风险等级：

### 🟢 低风险 → 直接执行
- 在 `src/` 下编辑/创建 Python 文件
- 在 `docs/` 下添加或修改测试文档
- 在项目根目录生成 HTML/文档文件
- 运行 `python check_env.py` 等只读检查
- pip install 到 `rag-env/` 虚拟环境内

### 🟡 中风险 → 告知后执行
- 修改 .env 或 .env.example（涉及密钥配置）
- 修改 requirements.txt（影响依赖版本）
- 修改 CLAUDE.md（影响后续工作行为）
- pip install 到系统全局 Python
- 创建新的顶级目录

### 🔴 高风险 → 必须征得同意
- 删除项目外的任何文件/目录
- 修改系统环境变量（PATH、注册表等）
- 在项目目录外创建文件
- `rm -rf`、`git push --force` 等不可逆操作
- 涉及 C 盘的写入操作
- 安装系统级软件

## 项目边界约束

- 所有代码、数据、配置 **必须** 在 `D:\vibecoding\project1\` 内
- 虚拟环境在 `rag-env/`，Python 包不污染系统
- ChromaDB 数据在 `chroma_data/`，可随时删除重建
- .env 不提交到 Git（已在 .gitignore 中）

## 技术栈速查

| 层 | 方案 |
|-----|------|
| LLM | DeepSeek (deepseek-chat)，OpenAI 备选 |
| Embedding | 本地 BGE-M3，免费免联网 |
| 向量库 | ChromaDB，本地持久化 |
| 解析 | markdown-it-py / pdfplumber / python-docx / BeautifulSoup |
| UI | CLI → Streamlit |
