"""
统一的知识图谱查询日志记录工具。

用于在不同模块（Flask接口、GraphRAG 查询节点等）之间共享
knowledge_query.log 的写入逻辑，避免分散实现导致日志缺失。
"""

import json
import threading
from datetime import datetime
from pathlib import Path

from loguru import logger

# 日志文件路径
ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
KNOWLEDGE_LOG_FILE = LOG_DIR / "knowledge_query.log"

_log_lock = threading.Lock()


def _sanitize_log_text(text: str) -> str:
    """移除换行/回车，防止日志污染。"""
    return str(text).replace("\n", " ").replace("\r", " ").strip()


def _trim_text(text: str, limit: int = 300) -> str:
    """对长文本进行截断，避免日志过长。"""
    text = _sanitize_log_text(text)
    return text if len(text) <= limit else text[:limit] + "..."


def compact_records(items):
    """
    将节点/记录压缩为简洁日志格式，避免日志被大字段污染。
    """
    compacted = []
    if not items:
        return compacted

    for item in items:
        if not isinstance(item, dict):
            compacted.append(_trim_text(str(item)))
            continue

        entry = {}
        for key, value in item.items():
            if isinstance(value, (str, int, float, bool)):
                entry[key] = _trim_text(str(value))
            else:
                try:
                    entry[key] = _trim_text(json.dumps(value, ensure_ascii=False))
                except Exception:
                    entry[key] = _trim_text(str(value))
        compacted.append(entry)
    return compacted


def init_knowledge_log(force_reset: bool = True):
    """
    初始化知识库查询日志文件。

    Args:
        force_reset: True 时重置文件并写入初始化标记；False 时仅在文件不存在时写入。
    """
    try:
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        mode = "w" if force_reset or not KNOWLEDGE_LOG_FILE.exists() else "a"
        with _log_lock, open(KNOWLEDGE_LOG_FILE, mode, encoding="utf-8") as f:
            f.write(f"=== Knowledge Query Log 初始化 - {start_time} ===\n")
        logger.info("Knowledge Query: knowledge_query.log 已初始化")
    except Exception as exc:  # pragma: no cover - 仅运行时执行
        logger.exception(f"Knowledge Query: 初始化日志失败: {exc}")


def _ensure_log_file():
    """确保日志文件已创建且可写，不会覆盖现有内容。"""
    if not KNOWLEDGE_LOG_FILE.exists():
        init_knowledge_log(force_reset=False)


def append_knowledge_log(source: str, payload: dict):
    """记录知识库查询关键词与完整请求数据。"""
    try:
        _ensure_log_file()
        timestamp = datetime.now().strftime("%H:%M:%S")
        clean_source = _sanitize_log_text(source or "UNKNOWN")
        serialized = json.dumps(payload, ensure_ascii=False)
        sanitized = _sanitize_log_text(serialized)
        with _log_lock, open(KNOWLEDGE_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [KNOWLEDGE] [{clean_source}] {sanitized}\n")
    except Exception as exc:  # pragma: no cover - 日志失败不影响主流程
        logger.warning(f"Knowledge Query: 写日志失败: {exc}")
