"""
知识图谱构建器

基于结构化的 State JSON 和 Forum 日志构建知识图谱，无需 LLM 提取实体。
"""

from typing import Dict, List, Optional
import hashlib

from .state_parser import ParsedState, ParsedSection
from .forum_parser import ForumEntry
from .graph_storage import Graph, Node


class GraphBuilder:
    """
    知识图谱构建器
    
    基于已有的结构化数据（State JSON、Forum 日志）构建图谱，
    无需 LLM 进行实体/关系提取。
    
    ReportAgent 在 _build_knowledge_graph 中调用本构建器，将 load_input_files
    提前解析好的 ParsedState / ForumEntry 转为 Graph 对象，再交由 GraphStorage
    落盘并供 GraphRAGQueryNode 查询。
    
    节点类型（5种）:
    - topic: 用户查询主题
    - engine: 四个引擎来源 (insight/media/query/host)
    - section: 报告段落/章节
    - search_query: 搜索关键词
    - source: 信息来源 URL
    
    关系类型（4种）:
    - analyzed_by: 主题由引擎分析 (Topic → Engine)
    - contains: 引擎包含段落 (Engine → Section)
    - searched: 段落执行搜索 (Section → SearchQuery)
    - found: 搜索发现来源 (SearchQuery → Source)
    """
    
    def build(self, topic: str, states: Dict[str, ParsedState],
              forum_entries: Optional[List[ForumEntry]] = None) -> Graph:
        """
        构建知识图谱
        
        Args:
            topic: 用户查询主题
            states: 引擎状态字典 {engine_name: ParsedState}
            forum_entries: Forum 日志条目列表
            
        Returns:
            构建的 Graph 对象
        """
        graph = Graph()
        
        # 1. 创建主题节点
        topic_node = graph.add_node(
            node_type="topic",
            name=topic,
            node_id=f"T_{self._hash(topic)}"
        )
        
        # 2. 处理每个引擎的状态
        for engine_name, state in states.items():
            self._add_engine_nodes(graph, topic_node, engine_name, state)
        
        # 3. 处理 Forum 日志（添加 Host 节点）
        if forum_entries:
            self._add_forum_nodes(graph, topic_node, forum_entries)
        
        return graph
    
    def _add_engine_nodes(self, graph: Graph, topic_node: Node,
                          engine_name: str, state: ParsedState) -> None:
        """添加引擎相关节点"""
        # 创建引擎节点
        engine_node = graph.add_node(
            node_type="engine",
            name=engine_name,
            node_id=engine_name,
            report_title=state.report_title,
            original_query=state.query
        )
        
        # Topic → Engine 关系
        graph.add_edge(topic_node, engine_node, "analyzed_by")
        
        # 处理段落
        for section in state.sections:
            self._add_section_nodes(graph, engine_node, engine_name, section)
    
    def _add_section_nodes(self, graph: Graph, engine_node: Node,
                           engine_name: str, section: ParsedSection) -> None:
        """添加段落相关节点"""
        # 创建段落节点
        section_id = f"{engine_name}_S{section.order}"
        section_node = graph.add_node(
            node_type="section",
            name=section.title,
            node_id=section_id,
            title=section.title,
            order=section.order,
            summary=section.summary,
            engine=engine_name
        )
        
        # Engine → Section 关系
        graph.add_edge(engine_node, section_node, "contains")
        
        # 处理搜索历史
        seen_queries = set()  # 去重
        for idx, search in enumerate(section.search_history):
            if not search.query:
                continue
            
            # 搜索词去重（同一段落相同查询仅保留首条，避免图谱冗余）
            query_key = search.query.strip().lower()
            if query_key in seen_queries:
                continue
            seen_queries.add(query_key)
            
            # 创建搜索词节点
            query_id = f"{section_id}_Q{idx}"
            query_node = graph.add_node(
                node_type="search_query",
                name=search.query[:50],  # 截断长查询
                node_id=query_id,
                query_text=search.query,
                section_ref=section_id,
                engine=engine_name
            )
            
            # Section → SearchQuery 关系
            graph.add_edge(section_node, query_node, "searched")
            
            # 处理来源
            if search.url:
                self._add_source_node(graph, query_node, search)
    
    def _add_source_node(self, graph: Graph, query_node: Node,
                         search) -> None:
        """添加来源节点"""
        # 使用 URL 的哈希作为 ID，避免重复
        source_id = f"SRC_{self._hash(search.url)}"
        
        # 检查是否已存在
        existing = graph.get_node(source_id)
        if existing:
            source_node = existing
        else:
            source_node = graph.add_node(
                node_type="source",
                name=search.title[:50] if search.title else search.url[:50],
                node_id=source_id,
                url=search.url,
                title=search.title,
                preview=search.content[:100] if search.content else '',
                score=search.score
            )
        
        # SearchQuery → Source 关系
        graph.add_edge(query_node, source_node, "found")
    
    def _add_forum_nodes(self, graph: Graph, topic_node: Node,
                         entries: List[ForumEntry]) -> None:
        """添加 Forum 日志相关节点"""
        # 创建 Host 引擎节点（如果不存在）
        host_node = graph.get_node('host')
        if not host_node:
            host_node = graph.add_node(
                node_type="engine",
                name="host",
                node_id="host",
                report_title="论坛主持人总结"
            )
            graph.add_edge(topic_node, host_node, "analyzed_by")
        
        # 提取 Host 的关键发言作为 Section
        host_entries = [e for e in entries if e.is_host and not e.is_system]
        
        for idx, entry in enumerate(host_entries[:5]):  # 最多取 5 条
            section_id = f"host_S{idx}"
            section_node = graph.add_node(
                node_type="section",
                name=f"主持人总结 {idx + 1}",
                node_id=section_id,
                title=f"[{entry.timestamp}] 主持人总结",
                order=idx,
                summary=entry.content[:300],
                engine="host",
                timestamp=entry.timestamp
            )
            
            graph.add_edge(host_node, section_node, "contains")
    
    @staticmethod
    def _hash(text: str) -> str:
        """生成短哈希"""
        return hashlib.md5(text.encode()).hexdigest()[:8]
