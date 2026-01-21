"""
知识图谱存储模块

定义图谱的核心数据结构（Node、Edge、Graph）及 JSON 存储功能。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
import re
from datetime import datetime
import json
from pathlib import Path
import hashlib


@dataclass
class Node:
    """图谱节点"""
    id: str
    type: str  # topic, engine, section, search_query, source
    name: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def label(self) -> str:
        """获取显示标签（兼容前端）"""
        return self.name
    
    @property
    def properties(self) -> Dict[str, Any]:
        """获取属性（兼容前端）"""
        return self.attributes
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'type': self.type,
            'name': self.name,
            'label': self.name,  # 兼容字段
            'attributes': self.attributes,
            'properties': self.attributes  # 兼容字段
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """从字典创建"""
        return cls(
            id=data['id'],
            type=data['type'],
            name=data.get('name', data.get('label', '')),
            attributes=data.get('attributes', data.get('properties', {}))
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取属性值"""
        if key == 'id':
            return self.id
        if key == 'type':
            return self.type
        if key in ('name', 'label'):
            return self.name
        return self.attributes.get(key, default)


@dataclass
class Edge:
    """图谱边"""
    from_id: str
    to_id: str
    relation: str  # analyzed_by, contains, searched, found
    weight: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def source(self) -> str:
        """起始节点ID（兼容前端）"""
        return self.from_id
    
    @property
    def target(self) -> str:
        """目标节点ID（兼容前端）"""
        return self.to_id
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'from': self.from_id,
            'to': self.to_id,
            'source': self.from_id,  # 兼容字段
            'target': self.to_id,    # 兼容字段
            'relation': self.relation,
            'weight': self.weight,
            'attributes': self.attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Edge':
        """从字典创建"""
        return cls(
            from_id=data.get('from', data.get('source', '')),
            to_id=data.get('to', data.get('target', '')),
            relation=data['relation'],
            weight=data.get('weight', 1.0),
            attributes=data.get('attributes', {})
        )


class Graph:
    """
    知识图谱
    
    仅负责存储节点/边与邻接表，不依赖外部数据库，便于在章节侧内存查询。
    邻接表 _adjacency 用于 QueryEngine 按深度扩展邻居节点。
    """
    
    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._adjacency: Dict[str, Set[str]] = {}  # 邻接表
        
    @property
    def nodes(self) -> Dict[str, Node]:
        """获取所有节点（字典形式，兼容前端API）"""
        return self._nodes
    
    @property
    def node_list(self) -> List[Node]:
        """获取所有节点（列表形式）"""
        return list(self._nodes.values())
    
    @property
    def edges(self) -> List[Edge]:
        """获取所有边"""
        return self._edges
    
    @property
    def node_count(self) -> int:
        """节点数量"""
        return len(self._nodes)
    
    @property
    def edge_count(self) -> int:
        """边数量"""
        return len(self._edges)
    
    def add_node(self, node_type: str, name: str = "", 
                 node_id: Optional[str] = None, **attributes) -> Node:
        """
        添加节点
        
        Args:
            node_type: 节点类型
            name: 节点名称
            node_id: 节点ID，不提供则自动生成
            **attributes: 其他属性
            
        Returns:
            创建的节点
        """
        if node_id is None:
            # 基于类型和名称生成ID
            hash_input = f"{node_type}_{name}_{len(self._nodes)}"
            node_id = f"{node_type[:3].upper()}_{hashlib.md5(hash_input.encode()).hexdigest()[:8]}"
        
        # 如果已存在，返回现有节点
        if node_id in self._nodes:
            return self._nodes[node_id]
        
        node = Node(
            id=node_id,
            type=node_type,
            name=name,
            attributes=attributes
        )
        
        self._nodes[node_id] = node
        self._adjacency[node_id] = set()
        
        return node
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """获取节点"""
        return self._nodes.get(node_id)
    
    def add_edge(self, from_node: Node, to_node: Node, 
                 relation: str, weight: float = 1.0, **attributes) -> Edge:
        """
        添加边
        
        Args:
            from_node: 起始节点
            to_node: 目标节点
            relation: 关系类型
            weight: 权重
            **attributes: 其他属性
            
        Returns:
            创建的边
        """
        edge = Edge(
            from_id=from_node.id,
            to_id=to_node.id,
            relation=relation,
            weight=weight,
            attributes=attributes
        )
        
        self._edges.append(edge)
        
        # 更新邻接表
        if from_node.id in self._adjacency:
            self._adjacency[from_node.id].add(to_node.id)
        if to_node.id in self._adjacency:
            self._adjacency[to_node.id].add(from_node.id)
        
        return edge
    
    def get_neighbors(self, node_id: str) -> List[Node]:
        """获取邻居节点"""
        neighbor_ids = self._adjacency.get(node_id, set())
        return [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]
    
    def get_edges_from(self, node_id: str) -> List[Edge]:
        """获取从指定节点出发的边"""
        return [e for e in self._edges if e.from_id == node_id]
    
    def get_edges_to(self, node_id: str) -> List[Edge]:
        """获取指向指定节点的边"""
        return [e for e in self._edges if e.to_id == node_id]
    
    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """按类型获取节点"""
        return [n for n in self._nodes.values() if n.type == node_type]
    
    def get_stats(self) -> Dict[str, int]:
        """获取图谱统计信息"""
        type_counts = {}
        for node in self._nodes.values():
            type_counts[node.type] = type_counts.get(node.type, 0) + 1
        
        return {
            'total_nodes': self.node_count,
            'total_edges': self.edge_count,
            **type_counts
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取图谱概览（用于提示词）"""
        stats = self.get_stats()
        
        # 获取各类型节点的样例
        section_titles = [n.name for n in self.get_nodes_by_type('section')][:10]
        search_queries = [n.get('query_text', n.name) 
                         for n in self.get_nodes_by_type('search_query')][:20]
        
        return {
            'stats': stats,
            'section_titles': section_titles,
            'sample_queries': search_queries,
            'topic': next((n.name for n in self.get_nodes_by_type('topic')), ''),
            'engines': [n.name for n in self.get_nodes_by_type('engine')]
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'nodes': [n.to_dict() for n in self.node_list],
            'edges': [e.to_dict() for e in self.edges],
            'stats': self.get_stats()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Graph':
        """从字典创建"""
        graph = cls()
        
        # 添加节点
        for node_data in data.get('nodes', []):
            node = Node.from_dict(node_data)
            graph._nodes[node.id] = node
            graph._adjacency[node.id] = set()
        
        # 添加边
        for edge_data in data.get('edges', []):
            edge = Edge.from_dict(edge_data)
            graph._edges.append(edge)
            # 更新邻接表
            if edge.from_id in graph._adjacency:
                graph._adjacency[edge.from_id].add(edge.to_id)
            if edge.to_id in graph._adjacency:
                graph._adjacency[edge.to_id].add(edge.from_id)
        
        return graph


class GraphStorage:
    """
    图谱存储管理器
    
    将 Graph 对象序列化为 JSON（graphrag.json），路径与 ChapterStorage 输出目录一致，
    便于 Web/Report 引擎共享。支持按报告ID查找、列举最新图谱，供 Flask API 或
    GraphRAGQueryNode 直接读取。
    """
    
    FILENAME = "graphrag.json"

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        """统一规约ID，去除分隔符便于模糊匹配。"""
        return re.sub(r'[^a-zA-Z0-9]', '', str(value or '')).lower()

    def _graph_file_matches(self, graph_path: Path, normalized_target: str) -> bool:
        """检查图文件中的 task_id/report_id 是否与目标匹配。"""
        try:
            with open(graph_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            candidates = [
                data.get('task_id'),
                data.get('report_id'),
                data.get('metadata', {}).get('report_id') if isinstance(data.get('metadata'), dict) else None
            ]
            for candidate in candidates:
                if candidate and self._normalize_identifier(candidate) == normalized_target:
                    return True
        except Exception:
            return False
        return False
    
    @property
    def chapters_dir(self) -> Path:
        """获取章节目录路径（与 ChapterStorage 保持一致）"""
        try:
            from ..utils.config import settings
            return Path(settings.CHAPTER_OUTPUT_DIR)
        except ImportError:
            # 回退到默认值
            return Path("final_reports/chapters")
    
    def save(self, graph: Graph, task_id: str, run_dir: Path) -> Path:
        """
        保存图谱到 JSON 文件
        
        Args:
            graph: 图谱对象
            task_id: 任务ID
            run_dir: 运行目录
            
        Returns:
            保存的文件路径
        """
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        
        output = {
            'task_id': task_id,
            'created_at': datetime.now().isoformat(),
            **graph.to_dict()
        }
        
        file_path = run_dir / self.FILENAME
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    def load(self, path: Path) -> Optional[Graph]:
        """
        从 JSON 文件加载图谱
        
        Args:
            path: 文件路径或运行目录
            
        Returns:
            Graph 对象，失败返回 None
        """
        path = Path(path)
        
        # 如果是目录，添加文件名
        if path.is_dir():
            file_path = path / self.FILENAME
        else:
            file_path = path
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Graph.from_dict(data)
        except Exception:
            return None
    
    def exists(self, run_dir: Path) -> bool:
        """检查图谱文件是否存在"""
        return (Path(run_dir) / self.FILENAME).exists()
    
    def find_graph_by_report_id(self, report_id: str) -> Optional[Path]:
        """
        根据报告ID查找图谱文件
        
        Args:
            report_id: 报告ID
            
        Returns:
            图谱文件路径，未找到返回 None
        
        工作方式：
        1) 优先匹配目录名是否含 report_id（兼容 _/- 差异）；
        2) 否则读取 graphrag.json 内 task_id/report_id 做兜底匹配；
        适配 Agent 运行目录命名不一致的场景。
        """
        # 在章节目录中搜索（与 ChapterStorage 保持一致）
        chapters_dir = self.chapters_dir
        if not chapters_dir.exists():
            return None
        if not report_id:
            return None

        # 兼容不同分隔符（report-xxx 与 report_xxx）以及简化匹配
        normalized_target = self._normalize_identifier(report_id)
        alt_targets = {
            str(report_id),
            str(report_id).replace('_', '-'),
            str(report_id).replace('-', '_'),
        }
        fallback_match: Optional[Path] = None
        
        # 查找匹配报告ID的目录
        for run_dir in chapters_dir.iterdir():
            if not run_dir.is_dir():
                continue
            
            name = run_dir.name
            normalized_name = self._normalize_identifier(name)

            # 检查目录名是否包含报告ID或归一化后相等
            if (
                any(t for t in alt_targets if t and t in name)
                or normalized_name == normalized_target
            ):
                graph_path = run_dir / self.FILENAME
                if graph_path.exists():
                    return graph_path

            # 若目录名不匹配，则尝试读取文件内容比对 task_id/report_id
            graph_path = run_dir / self.FILENAME
            if graph_path.exists() and not fallback_match:
                if self._graph_file_matches(graph_path, normalized_target):
                    fallback_match = graph_path
        
        return fallback_match
    
    def find_latest_graph(self) -> Optional[Path]:
        """
        查找最新的图谱文件
        
        Returns:
            最新图谱文件路径，未找到返回 None
        
        根据文件修改时间排序，用于前端“最近一次生成”快速预览。
        """
        chapters_dir = self.chapters_dir
        if not chapters_dir.exists():
            return None
        
        latest_path = None
        latest_time = None
        
        # 遍历所有运行目录
        for run_dir in chapters_dir.iterdir():
            if not run_dir.is_dir():
                continue
            
            graph_path = run_dir / self.FILENAME
            if graph_path.exists():
                mtime = graph_path.stat().st_mtime
                if latest_time is None or mtime > latest_time:
                    latest_time = mtime
                    latest_path = graph_path
        
        return latest_path
    
    def list_all_graphs(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的图谱
        
        Returns:
            图谱信息列表，包含路径、报告ID、创建时间等
        """
        chapters_dir = self.chapters_dir
        if not chapters_dir.exists():
            return []
        
        graphs = []
        for run_dir in chapters_dir.iterdir():
            if not run_dir.is_dir():
                continue
            
            graph_path = run_dir / self.FILENAME
            if graph_path.exists():
                try:
                    with open(graph_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    graphs.append({
                        'path': str(graph_path),
                        'report_id': data.get('task_id', run_dir.name),
                        'created_at': data.get('created_at'),
                        'stats': data.get('stats', {}),
                        'dir_name': run_dir.name
                    })
                except Exception:
                    continue
        
        # 按创建时间排序
        graphs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return graphs
