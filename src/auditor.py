"""索引审计: 对比原始文件 / manifest / ChromaDB 三方数据，输出报告"""

import json
import re
from pathlib import Path
from datetime import datetime
from .config import DOCS_DIR, SUPPORTED_EXTENSIONS, CHROMA_PERSIST_DIR
from .chroma_store import ChromaStore
from .bm25_index import get_shared_bm25


class IngestAuditor:
    def __init__(self, docs_dir: str | None = None):
        self.docs_dir = Path(docs_dir or DOCS_DIR).resolve()
        self.store = ChromaStore(bm25_index=get_shared_bm25())
        self._manifest_path = Path(CHROMA_PERSIST_DIR).resolve() / "manifest.json"
        self._tdoc_pattern = re.compile(r"[Rr]\d-?\d{6,7}")

    def run(self) -> dict:
        manifest = self._load_manifest()
        disk_files = self._scan_disk()
        chroma_stats = self.store.get_all_source_stats()

        report = {
            "audit_time": datetime.now().isoformat(),
            "summary": {},
            "processed": [],
            "pending": [],
            "failed": [],
            "duplicate": [],
            "suspicious": [],
        }

        all_tdoc_files: dict[str, list[str]] = {}  # tdoc_num → [rel_paths]

        for rel_path, info in sorted(disk_files.items()):
            abs_path = str(self.docs_dir / rel_path)
            mtime = info["mtime"]
            size = info["size"]
            in_manifest = rel_path in manifest
            manifest_mtime = manifest.get(rel_path, 0)
            chunk_count = chroma_stats.get(abs_path, 0)

            # TDoc 重复检测
            tdoc_nums = self._extract_tdocs(rel_path)
            for tn in tdoc_nums:
                all_tdoc_files.setdefault(tn, []).append(rel_path)

            # 分类
            status, reason = self._classify(
                in_manifest=in_manifest,
                manifest_mtime=manifest_mtime,
                disk_mtime=mtime,
                chunk_count=chunk_count,
                file_size=size,
            )

            entry = {
                "rel_path": rel_path,
                "abs_path": abs_path,
                "file_size": size,
                "mtime": mtime,
                "in_manifest": in_manifest,
                "chunk_count": chunk_count,
                "status": status,
                "reason": reason,
                "tdocs": tdoc_nums,
            }

            if status == "processed":
                report["processed"].append(entry)
            elif status == "pending":
                report["pending"].append(entry)
            elif status == "failed":
                report["failed"].append(entry)
            elif status == "suspicious":
                report["suspicious"].append(entry)

        # 检测 TDoc 重复
        for tdoc_num, paths in all_tdoc_files.items():
            if len(paths) > 1:
                report["duplicate"].append({
                    "tdoc": tdoc_num,
                    "files": paths,
                    "count": len(paths),
                })

        # 检测 manifest 中有但磁盘已删除的文件
        deleted = []
        for rel_path in manifest:
            if rel_path not in disk_files:
                abs_path = str(self.docs_dir / rel_path)
                deleted.append({
                    "rel_path": rel_path,
                    "abs_path": abs_path,
                    "chunk_count": chroma_stats.get(abs_path, 0),
                    "status": "deleted_on_disk",
                })
        if deleted:
            report["suspicious"].extend(deleted)

        # 汇总
        report["summary"] = {
            "total_disk_files": len(disk_files),
            "total_manifest_entries": len(manifest),
            "total_chroma_chunks": self.store.count(),
            "total_chroma_sources": len(chroma_stats),
            "processed": len(report["processed"]),
            "pending": len(report["pending"]),
            "failed": len(report["failed"]),
            "duplicate_tdocs": len(report["duplicate"]),
            "suspicious": len(report["suspicious"]),
            "bm25_entries": len(self.store._bm25) if self.store._bm25 else 0,
        }

        return report

    def _classify(
        self, *, in_manifest: bool, manifest_mtime: float,
        disk_mtime: float, chunk_count: int, file_size: int,
    ) -> tuple[str, str]:
        if file_size == 0:
            return "suspicious", "empty_file"

        if not in_manifest:
            return "pending", "not_in_manifest"

        if chunk_count == 0:
            return "failed", "in_manifest_no_chunks"

        if abs(manifest_mtime - disk_mtime) > 1:
            return "pending", "file_modified_since_index"

        # chunk 数异常低（>100KB 的 docx 却只有 1-2 chunks）
        if file_size > 100_000 and chunk_count <= 2:
            return "suspicious", f"low_chunks: {file_size:,}B → {chunk_count} chunks"

        return "processed", "ok"

    def _load_manifest(self) -> dict[str, float]:
        if not self._manifest_path.exists():
            return {}
        try:
            return json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _scan_disk(self) -> dict[str, dict]:
        if not self.docs_dir.exists():
            return {}
        files = {}
        for ext in SUPPORTED_EXTENSIONS:
            for p in self.docs_dir.rglob(f"*{ext}"):
                rel = str(p.relative_to(self.docs_dir))
                st = p.stat()
                files[rel] = {"mtime": st.st_mtime, "size": st.st_size}
        return files

    def _extract_tdocs(self, rel_path: str) -> list[str]:
        return self._tdoc_pattern.findall(rel_path)

    # ── 报告输出 ──────────────────────────────────

    def save_report(self, report: dict, output_dir: str = "."):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # JSON
        json_path = out / "ingest_audit_report.json"
        json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"[AUDIT] JSON → {json_path}")

        # Markdown
        md_path = out / "ingest_audit_report.md"
        md_path.write_text(self._to_markdown(report), encoding="utf-8")
        print(f"[AUDIT] MD   → {md_path}")

    def _to_markdown(self, r: dict) -> str:
        s = r["summary"]
        lines = [
            f"# 3GPP 索引审计报告",
            f"**审计时间**: {r['audit_time']}",
            "",
            "## 概要",
            f"| 项 | 值 |",
            f"|----|-----|",
            f"| 磁盘文件数 | {s['total_disk_files']} |",
            f"| Manifest 条目 | {s['total_manifest_entries']} |",
            f"| ChromaDB chunks 总数 | {s['total_chroma_chunks']} |",
            f"| ChromaDB 来源文件数 | {s['total_chroma_sources']} |",
            f"| BM25 条目 | {s['bm25_entries']} |",
            "",
            "| 状态 | 数量 |",
            "|------|------|",
            f"| ✅ Processed | {s['processed']} |",
            f"| ⏳ Pending | {s['pending']} |",
            f"| ❌ Failed | {s['failed']} |",
            f"| 🔄 Duplicate TDoc | {s['duplicate_tdocs']} |",
            f"| ⚠️ Suspicious | {s['suspicious']} |",
            "",
        ]

        if r["processed"]:
            lines.append("## ✅ Processed")
            lines.append("| 文件 | Chunks | Size | TDoc |")
            lines.append("|------|--------|------|------|")
            for e in r["processed"]:
                tdocs = ",".join(e.get("tdocs", [])[:3]) or "-"
                lines.append(f"| {e['rel_path']} | {e['chunk_count']} | {e['file_size']:,}B | {tdocs} |")

        if r["pending"]:
            lines.append("\n## ⏳ Pending")
            lines.append("| 文件 | Size | 原因 | TDoc |")
            lines.append("|------|------|------|------|")
            for e in r["pending"][:30]:
                tdocs = ",".join(e.get("tdocs", [])[:3]) or "-"
                lines.append(f"| {e['rel_path']} | {e['file_size']:,}B | {e['reason']} | {tdocs} |")

        if r["failed"]:
            lines.append("\n## ❌ Failed")
            for e in r["failed"]:
                lines.append(f"- `{e['rel_path']}` — {e['reason']} (size={e['file_size']:,}B)")

        if r["duplicate"]:
            lines.append("\n## 🔄 Duplicate TDoc")
            for d in r["duplicate"]:
                lines.append(f"- **{d['tdoc']}** ×{d['count']}:")
                for f in d["files"]:
                    lines.append(f"  - `{f}`")

        if r["suspicious"]:
            lines.append("\n## ⚠️ Suspicious")
            for e in r["suspicious"]:
                lines.append(f"- `{e.get('rel_path','?')}` — {e.get('reason','?')} (chunks={e.get('chunk_count','?')})")

        lines.append(f"\n---\n*Generated by IngestAuditor*")
        return "\n".join(lines)
