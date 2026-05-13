3GPP 文档库目录结构
====================

把下载的 3GPP 文档放到对应子目录:

  tdocs/     — 技术文档 (TDoc), 如 R1-2401234.docx
  specs/     — 技术规范/报告 (TS/TR), 如 TS 38.355.pdf
  meetings/  — 会议纪要/报告, 如 RAN1#119bis_report.docx
  cr/        — 标准修改请求 (Change Request), 如 CR-1234.docx

支持格式: .docx .pdf .txt .md .html

放好文档后，运行索引:
  python -c "from src.ingest import IngestPipeline; IngestPipeline().run(clear=True)"

或用 Streamlit UI 侧边栏的"重新索引"按钮。
