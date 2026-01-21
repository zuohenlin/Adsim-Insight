"""
图查询引擎

支持基于关键词、节点类型、引擎来源和深度的知识图谱查询。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set

from .graph_storage import Graph, Node


@dataclass
class QueryParams:
    """
    查询参数
    
    由 GraphRAGQueryNode 或 Flask API 注入，控制查询范围：
    - keywords: 关键词列表，可为空（空时默认返回各引擎 section 摘要）；
    - node_types: 限定节点类型；None 表示全量；
    - engine_filter: 仅保留指定引擎来源；
    - depth: 匹配节点向外扩展的层级。
    """
    keywords: List[str] = field(default_factory=list)
    node_types: Optional[List[str]] = None  # None 表示全部类型
    engine_filter: Optional[List[str]] = None  # 限定引擎来源
    depth: int = 1  # 扩展深度
    # 结果数量限制（防止空关键词时返回整个图谱）
    max_sections: int = 15
    max_queries: int = 20
    max_sources: int = 10


@dataclass
class QueryResult:
    """查询结果"""
    matched_sections: List[Dict[str, Any]] = field(default_factory=list)
    matched_queries: List[Dict[str, Any]] = field(default_factory=list)
    matched_sources: List[Dict[str, Any]] = field(default_factory=list)
    total_nodes: int = 0
    query_params: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'matched_sections': self.matched_sections,
            'matched_queries': self.matched_queries,
            'matched_sources': self.matched_sources,
            'total_nodes': self.total_nodes,
            'query_params': self.query_params
        }
    
    def get_summary(self, max_length: int = 200) -> str:
        """获取结果摘要"""
        parts = []
        
        if self.matched_sections:
            section_titles = [s.get('title', '')[:30] for s in self.matched_sections[:3]]
            parts.append(f"段落({len(self.matched_sections)}): {', '.join(section_titles)}")
        
        if self.matched_queries:
            query_texts = [q.get('query_text', '')[:20] for q in self.matched_queries[:3]]
            parts.append(f"搜索词({len(self.matched_queries)}): {', '.join(query_texts)}")
        
        if self.matched_sources:
            parts.append(f"来源({len(self.matched_sources)})")
        
        summary = "; ".join(parts) if parts else "无匹配结果"
        return summary[:max_length]


class QueryEngine:
    """
    图查询引擎
    
    支持以下查询能力：
    1. 关键词匹配：在节点名称和属性中搜索
    2. 类型筛选：限定节点类型 (section/search_query/source)
    3. 引擎筛选：限定来源引擎 (insight/media/query/host)
    4. 深度扩展：从匹配节点向外扩展指定深度
    """
    
    def __init__(self, graph: Graph):
        """
        初始化查询引擎
        
        Args:
            graph: 知识图谱对象
        """
        self.graph = graph
    
    def query(self, params: QueryParams) -> QueryResult:
        """
        执行图谱查询
        
        Args:
            params: 查询参数
            
        Returns:
            QueryResult 查询结果
        """
        # 1. 关键词匹配获取初始节点
        matched_nodes = self._match_keywords(params)
        
        # 2. 深度扩展
        if params.depth > 0 and matched_nodes:
            expanded_nodes = self._expand_depth(matched_nodes, params.depth)
            matched_nodes = matched_nodes.union(expanded_nodes)
        
        # 3. 整理结果
        result = self._organize_results(matched_nodes, params)
        
        return result
    
    def _match_keywords(self, params: QueryParams) -> Set[str]:
        """关键词匹配"""
        matched_ids = set()
        
        # 使用 .values() 遍历 Node 对象，而非字典键
        for node in self.graph.nodes.values():
            # 类型筛选
            if params.node_types and node.type not in params.node_types:
                continue
            
            # 引擎筛选
            if params.engine_filter:
                node_engine = node.get('engine')
                if node_engine and node_engine not in params.engine_filter:
                    continue
            
            # 关键词匹配
            if self._matches_keywords(node, params.keywords):
                matched_ids.add(node.id)
        
        return matched_ids
    
    def _matches_keywords(self, node: Node, keywords: List[str]) -> bool:
        """检查节点是否匹配关键词"""
        # 防御性检查：确保 keywords 为列表类型
        # 若传入字符串，逐字符迭代会导致单字符匹配（如 'a', 'e'），污染结果
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.replace(',', ' ').split() if k.strip()]
        elif not isinstance(keywords, list):
            keywords = []
        
        if not keywords:
            # 无关键词时：只匹配 section 类型（避免返回整个图谱）
            # 这样至少能获取到各引擎的段落摘要
            return node.type == 'section'
        
        # 构建搜索文本
        search_text = f"{node.name} {node.get('title', '')} {node.get('query_text', '')} {node.get('summary', '')}"
        search_text = search_text.lower()
        
        # 任一关键词匹配即可
        for keyword in keywords:
            if keyword.lower() in search_text:
                return True
        
        return False
    
    def _expand_depth(self, node_ids: Set[str], depth: int) -> Set[str]:
        """从匹配节点向外扩展指定深度"""
        expanded = set()
        current_layer = node_ids.copy()
        
        for _ in range(depth):
            next_layer = set()
            
            for node_id in current_layer:
                # 获取邻居节点
                neighbors = self.graph.get_neighbors(node_id)
                for neighbor in neighbors:
                    if neighbor.id not in node_ids and neighbor.id not in expanded:
                        next_layer.add(neighbor.id)
                        expanded.add(neighbor.id)
            
            if not next_layer:
                break
            
            current_layer = next_layer
        
        return expanded
    
    def _organize_results(self, node_ids: Set[str], 
                          params: QueryParams) -> QueryResult:
        """整理查询结果"""
        matched_sections = []
        matched_queries = []
        matched_sources = []
        
        for node_id in node_ids:
            node = self.graph.get_node(node_id)
            if not node:
                continue
            
            node_dict = {
                'id': node.id,
                'name': node.name,
                'type': node.type,
                **node.attributes
            }
            
            if node.type == 'section':
                matched_sections.append(node_dict)
            elif node.type == 'search_query':
                matched_queries.append(node_dict)
            elif node.type == 'source':
                matched_sources.append(node_dict)
        
        # 排序：段落按 order，其他按名称
        matched_sections.sort(key=lambda x: x.get('order', 0))
        matched_queries.sort(key=lambda x: x.get('query_text', ''))
        matched_sources.sort(key=lambda x: x.get('title', ''))
        
        # 应用结果数量限制（防止过多节点被注入提示词，超出 token 限制）
        limited_sections = matched_sections[:params.max_sections]
        limited_queries = matched_queries[:params.max_queries]
        limited_sources = matched_sources[:params.max_sources]
        
        return QueryResult(
            matched_sections=limited_sections,
            matched_queries=limited_queries,
            matched_sources=limited_sources,
            total_nodes=len(node_ids),  # 保留原始总数用于统计
            query_params={
                'keywords': params.keywords,
                'node_types': params.node_types,
                'engine_filter': params.engine_filter,
                'depth': params.depth
            }
        )
    
    def get_node_summary(self) -> Dict[str, Any]:
        """获取图谱节点概览（用于提示词）"""
        return self.graph.get_summary()
    
    def get_section_titles_by_engine(self) -> Dict[str, List[str]]:
        """按引擎获取所有段落标题"""
        result = {}
        
        for node in self.graph.get_nodes_by_type('section'):
            engine = node.get('engine', 'unknown')
            if engine not in result:
                result[engine] = []
            result[engine].append(node.get('title', node.name))
        
        return result
    
    def get_sample_search_queries(self, limit: int = 20) -> List[str]:
        """获取搜索词样例"""
        queries = []
        
        for node in self.graph.get_nodes_by_type('search_query'):
            query_text = node.get('query_text', node.name)
            if query_text and query_text not in queries:
                queries.append(query_text)
                if len(queries) >= limit:
                    break
        
        return queries
