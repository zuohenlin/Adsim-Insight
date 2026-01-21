"""
State JSON 解析器

解析 Insight/Media/Query 三引擎的 State JSON 文件，
提取结构化数据用于构建知识图谱。

默认假设 state_* 文件结构与三引擎输出一致：
- 顶层包含 query/report_title/paragraphs；
- 段落内的 research.search_history 记录搜索关键词、URL与摘要。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import json
from pathlib import Path


@dataclass
class SearchRecord:
    """单条搜索记录"""
    query: str = ""
    url: str = ""
    title: str = ""
    content: str = ""
    score: Optional[float] = None
    timestamp: str = ""


@dataclass
class ParsedSection:
    """解析后的段落/章节"""
    title: str = ""
    order: int = 0
    summary: str = ""
    search_history: List[SearchRecord] = field(default_factory=list)


@dataclass
class ParsedState:
    """解析后的引擎状态"""
    engine: str = ""
    query: str = ""
    report_title: str = ""
    sections: List[ParsedSection] = field(default_factory=list)


class StateParser:
    """
    State JSON 解析器
    
    解析三引擎的 State JSON，提取用于构建知识图谱的结构化数据。
    适用于 load_input_files 阶段：先查找与 MD 同目录的 state_*.json，
    若存在则转为 ParsedState 供 GraphBuilder 直接消费。
    """
    
    def parse(self, engine_name: str, state_json: Dict[str, Any]) -> ParsedState:
        """
        解析单个引擎的 State JSON
        
        Args:
            engine_name: 引擎名称 (insight/media/query)
            state_json: State JSON 字典
            
        Returns:
            ParsedState 对象
        """
        return ParsedState(
            engine=engine_name,
            query=state_json.get('query', ''),
            report_title=state_json.get('report_title', ''),
            sections=[
                self._parse_paragraph(p) 
                for p in state_json.get('paragraphs', [])
            ]
        )
    
    def _parse_paragraph(self, para: Dict[str, Any]) -> ParsedSection:
        """解析单个段落"""
        research = para.get('research', {})
        
        # 提取搜索历史
        search_history = []
        for search in research.get('search_history', []):
            search_history.append(SearchRecord(
                query=search.get('query', ''),
                url=search.get('url', ''),
                title=search.get('title', ''),
                content=search.get('content', '')[:200] if search.get('content') else '',
                score=search.get('score'),
                timestamp=search.get('timestamp', '')
            ))
        
        # 获取摘要，优先使用 latest_summary；若缺失则回退到段落正文
        summary = research.get('latest_summary', '')
        if not summary:
            summary = para.get('content', '')
        
        return ParsedSection(
            title=para.get('title', ''),
            order=para.get('order', 0),
            summary=summary[:300] if summary else '',
            search_history=search_history
        )
    
    def parse_from_file(self, engine_name: str, file_path: str) -> Optional[ParsedState]:
        """
        从文件解析 State JSON
        
        Args:
            engine_name: 引擎名称
            file_path: JSON 文件路径
            
        Returns:
            ParsedState 对象，失败返回 None
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                state_json = json.load(f)
            
            return self.parse(engine_name, state_json)
        except Exception:
            return None
    
    def find_state_json(self, md_path: str) -> Optional[str]:
        """
        根据 Markdown 报告路径查找对应的 State JSON 文件
        
        State JSON 通常与 MD 文件在同一目录下，命名格式为 state_*.json
        用于 GraphRAG：在 load_input_files 时自动匹配最新或同名 state 文件。
        
        Args:
            md_path: Markdown 文件路径
            
        Returns:
            State JSON 路径，未找到返回 None
        """
        md_file = Path(md_path)
        if not md_file.exists():
            return None
        
        parent_dir = md_file.parent
        
        # 尝试匹配 state_*.json 文件
        state_files = list(parent_dir.glob('state_*.json'))
        
        if not state_files:
            return None
        
        # 如果有多个，尝试通过时间戳匹配
        md_stem = md_file.stem  # e.g., "武汉大学_20250825_180214"
        
        for state_file in state_files:
            state_stem = state_file.stem  # e.g., "state_武汉大学_20250825_180214"
            # 检查是否包含相同的查询词和时间戳
            if md_stem in state_stem or state_stem.replace('state_', '') == md_stem:
                return str(state_file)
        
        # 否则返回最新的
        state_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return str(state_files[0])
