"""
GraphRAG 知识图谱模块

提供基于结构化数据的知识图谱构建、存储与查询功能。
典型用法：
1) 使用 `StateParser`/`ForumParser` 解析三引擎 state JSON 与 forum.log；
2) 调用 `GraphBuilder.build` 生成纯结构化的图对象；
3) 通过 `GraphStorage.save/load` 持久化或读取图数据；
4) 以 `QueryEngine` 在章节侧执行多轮图查询。
"""

from .state_parser import StateParser, ParsedState, ParsedSection, SearchRecord
from .forum_parser import ForumParser, ForumEntry
from .graph_builder import GraphBuilder
from .graph_storage import GraphStorage, Graph, Node, Edge
from .query_engine import QueryEngine, QueryParams, QueryResult

__all__ = [
    # 解析器
    'StateParser',
    'ParsedState',
    'ParsedSection', 
    'SearchRecord',
    'ForumParser',
    'ForumEntry',
    # 图谱核心
    'GraphBuilder',
    'GraphStorage',
    'Graph',
    'Node',
    'Edge',
    # 查询引擎
    'QueryEngine',
    'QueryParams',
    'QueryResult',
]
