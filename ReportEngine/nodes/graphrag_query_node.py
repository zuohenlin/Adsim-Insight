"""
GraphRAG 查询节点

负责与知识图谱交互，让 LLM 决定查询参数并执行多轮查询。
包含查询历史机制以防止重复查询。
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from loguru import logger
from utils.knowledge_logger import append_knowledge_log, compact_records

from .base_node import BaseNode
from ..llms.base import LLMClient
from ..graphrag.graph_storage import Graph
from ..graphrag.query_engine import QueryEngine, QueryParams, QueryResult
from ..graphrag.prompts import (
    GRAPHRAG_QUERY_DECISION_SYSTEM,
    GRAPHRAG_QUERY_DECISION_USER
)


@dataclass
class QueryRound:
    """单轮查询记录"""
    round: int
    params: Dict[str, Any]
    result_count: int
    summary: str


class QueryHistory:
    """
    查询历史记录器
    
    记录每次查询的参数和结果摘要，用于防止 LLM 重复查询相同内容。
    """
    
    def __init__(self):
        self.rounds: List[QueryRound] = []
    
    def add(self, params: Dict[str, Any], result: QueryResult) -> None:
        """
        记录一次查询
        
        Args:
            params: 查询参数
            result: 查询结果
        """
        self.rounds.append(QueryRound(
            round=len(self.rounds) + 1,
            params=params,
            result_count=result.total_nodes,
            summary=result.get_summary()
        ))
    
    def to_prompt(self) -> str:
        """
        生成供 LLM 参考的历史上下文
        
        Returns:
            格式化的历史记录字符串
        """
        if not self.rounds:
            return "（这是第1次查询，无历史记录）"
        
        lines = ["=== 已完成的查询历史 ==="]
        for r in self.rounds:
            keywords = r.params.get('keywords', [])
            node_types = r.params.get('node_types', ['all'])
            engine_filter = r.params.get('engine_filter', ['all'])
            
            lines.append(f"第{r.round}次查询:")
            lines.append(f"  关键词: {', '.join(keywords) if keywords else '无'}")
            lines.append(f"  节点类型: {', '.join(node_types) if node_types else '全部'}")
            lines.append(f"  引擎筛选: {', '.join(engine_filter) if engine_filter else '全部'}")
            lines.append(f"  返回节点数: {r.result_count}")
            lines.append(f"  结果摘要: {r.summary}")
            lines.append("")
        
        lines.append("=== 请避免重复上述查询，探索新的角度 ===")
        return "\n".join(lines)
    
    def get_all_keywords(self) -> List[str]:
        """获取所有已查询的关键词"""
        keywords = []
        for r in self.rounds:
            keywords.extend(r.params.get('keywords', []))
        return keywords


class GraphRAGQueryNode(BaseNode):
    """
    GraphRAG 查询节点
    
    核心职责：
    1. 接收完整上下文（报告、章节规划、图谱概览）
    2. 维护查询历史记录，防止重复查询
    3. 调用 LLM 决定查询参数
    4. 执行 GraphRAG 查询
    5. 最多允许 max_queries 次查询
    6. 将查询结果整合返回
    """
    
    def __init__(self, llm_client: LLMClient):
        super().__init__(llm_client, "GraphRAGQueryNode")
    
    def run(self, section: Dict[str, Any], context: Dict[str, Any],
            graph: Graph, max_queries: int = 3) -> Dict[str, Any]:
        """
        执行 GraphRAG 查询流程
        
        Args:
            section: 当前章节信息
            context: 生成上下文（报告、规划等）
            graph: 知识图谱
            max_queries: 最大查询次数
            
        Returns:
            合并后的查询结果
        """
        self.log_info(f"开始 GraphRAG 查询，章节: {section.get('title', 'unknown')}")
        chapter_id = section.get("id") or section.get("chapter_id") or section.get("chapterId")
        chapter_title = section.get("title", "unknown")
        
        query_engine = QueryEngine(graph)
        history = QueryHistory()
        all_results: List[QueryResult] = []
        
        for round_idx in range(max_queries):
            self.log_info(f"查询轮次 {round_idx + 1}/{max_queries}")
            
            # 1. 构建决策提示词：将章节目标+图谱概览+查询历史一起交给 LLM
            prompt = self._build_decision_prompt(
                section, context, query_engine, history
            )
            
            # 2. 调用 LLM 决定查询参数
            decision = self._get_query_decision(prompt)
            
            if decision is None:
                self.log_error("LLM 返回无效决策，终止查询")
                break
            
            # 3. 检查是否停止：LLM 可主动返回 should_query=false 以节省轮次
            if not decision.get('should_query', False):
                self.log_info(f"LLM 决定停止查询: {decision.get('reasoning', '无原因')}")
                break
            
            # 4. 执行查询：按 LLM 给出的参数查询本地图谱
            # 规范化 keywords：确保为列表类型（LLM 可能返回字符串）
            raw_keywords = decision.get('keywords', [])
            if isinstance(raw_keywords, str):
                # 按空格和逗号分割字符串为关键词列表
                raw_keywords = [k.strip() for k in raw_keywords.replace(',', ' ').split() if k.strip()]
            elif not isinstance(raw_keywords, list):
                raw_keywords = []
            
            params = QueryParams(
                keywords=raw_keywords,
                node_types=decision.get('node_types'),
                engine_filter=decision.get('engine_filter'),
                depth=decision.get('depth', 1)
            )
            params_dict = {
                'keywords': params.keywords,
                'node_types': params.node_types,
                'engine_filter': params.engine_filter,
                'depth': params.depth,
            }

            result = query_engine.query(params)
            all_results.append(result)
            
            self.log_info(f"查询返回 {result.total_nodes} 个节点")
            try:
                append_knowledge_log(
                    "GRAPH_QUERY_NODE",
                    {
                        "chapter_id": chapter_id or "",
                        "chapter_title": chapter_title,
                        "round": round_idx + 1,
                        "params": params_dict,
                        "result_counts": {
                            "matched_sections": len(result.matched_sections),
                            "matched_queries": len(result.matched_queries),
                            "matched_sources": len(result.matched_sources),
                            "total_nodes": result.total_nodes,
                        },
                        "matched_sections": compact_records(result.matched_sections[:5]),
                        "matched_queries": compact_records(result.matched_queries[:5]),
                        "matched_sources": compact_records(result.matched_sources[:5]),
                    },
                )
            except Exception as log_exc:  # pragma: no cover - 日志失败不阻塞流程
                logger.warning(f"Knowledge Query: GraphRAG 节点写日志失败: {log_exc}")
            
            # 5. 记录历史
            history.add(params_dict, result)
        
        # 6. 合并所有结果
        merged = self._merge_results(all_results)
        merged['query_rounds'] = len(all_results)
        
        self.log_info(f"GraphRAG 查询完成，共 {len(all_results)} 轮，"
                      f"获取 {merged.get('total_nodes', 0)} 个节点")
        try:
            append_knowledge_log(
                "GRAPH_QUERY_SUMMARY",
                {
                    "chapter_id": chapter_id or "",
                    "chapter_title": chapter_title,
                    "rounds": len(all_results),
                    "total_nodes": merged.get("total_nodes", 0),
                    "matched_sections": compact_records(merged.get("matched_sections", [])[:10]),
                    "matched_queries": compact_records(merged.get("matched_queries", [])[:10]),
                    "matched_sources": compact_records(merged.get("matched_sources", [])[:10]),
                    "cross_engine_insights": merged.get("cross_engine_insights", []),
                },
            )
        except Exception as log_exc:  # pragma: no cover - 日志失败不阻塞流程
            logger.warning(f"Knowledge Query: 汇总写日志失败: {log_exc}")
        
        return merged
    
    def _build_decision_prompt(self, section: Dict[str, Any],
                                context: Dict[str, Any],
                                query_engine: QueryEngine,
                                history: QueryHistory) -> Dict[str, str]:
        """
        构建查询决策提示词
        
        将章节目标、模板章节概览、图谱统计、历史查询摘要整合为
        system/user prompt，指导 LLM 生成下一轮 QueryParams。
        """
        # 获取图谱概览
        summary = query_engine.get_node_summary()
        stats = summary.get('stats', {})
        
        # 获取段落标题（按引擎分组）
        section_titles = query_engine.get_section_titles_by_engine()
        section_titles_text = ""
        for engine, titles in section_titles.items():
            section_titles_text += f"\n{engine}: {', '.join(titles[:5])}"
        
        # 获取搜索词样例
        sample_queries = query_engine.get_sample_search_queries(20)
        
        # 获取章节概览（word_plan 中的 chapters 使用 chapterId 而非 id）
        chapters = context.get('chapters', [])
        chapters_text = "\n".join([
            f"- {c.get('chapterId', c.get('id', ''))}: {c.get('title', c.get('display', ''))}"
            for c in chapters[:10]
        ])
        
        user_prompt = GRAPHRAG_QUERY_DECISION_USER.format(
            chapter_title=section.get('title', ''),
            chapter_id=section.get('id', ''),
            chapter_role=section.get('role', ''),
            target_words=section.get('target_words', 500),
            chapter_emphasis=section.get('emphasis', ''),
            report_topic=context.get('query', ''),
            template_name=context.get('template_name', ''),
            chapters_overview=chapters_text,
            topic_name=summary.get('topic', ''),
            engine_count=len(summary.get('engines', [])),
            section_count=stats.get('section', 0),
            query_count=stats.get('search_query', 0),
            source_count=stats.get('source', 0),
            section_titles_by_engine=section_titles_text,
            sample_search_queries=', '.join(sample_queries),
            query_history_detail=history.to_prompt()
        )
        
        return {
            'system': GRAPHRAG_QUERY_DECISION_SYSTEM,
            'user': user_prompt
        }
    
    def _get_query_decision(self, prompt: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        调用 LLM 获取查询决策
        
        返回的 JSON 将被转换为 QueryParams；任何解析失败都会终止后续轮次，
        避免章节生成被异常输出阻断。
        """
        try:
            response = self.llm_client.invoke(
                system_prompt=prompt['system'],
                user_prompt=prompt['user']
            )
            
            # 解析 JSON 响应
            return self._parse_json_response(response)
        except Exception as e:
            self.log_error(f"LLM 调用失败: {e}")
            return None
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 返回的 JSON"""
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试提取花括号内容
        brace_match = re.search(r'\{.*\}', response, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass
        
        self.log_error(f"无法解析 JSON 响应: {response[:200]}")
        return None
    
    def _merge_results(self, results: List[QueryResult]) -> Dict[str, Any]:
        """合并多轮查询结果"""
        merged = {
            'matched_sections': [],
            'matched_queries': [],
            'matched_sources': [],
            'total_nodes': 0,
            'cross_engine_insights': []
        }
        
        seen_section_ids = set()
        seen_query_ids = set()
        seen_source_ids = set()
        
        for result in results:
            # 合并段落（去重）
            for section in result.matched_sections:
                sid = section.get('id')
                if sid and sid not in seen_section_ids:
                    seen_section_ids.add(sid)
                    merged['matched_sections'].append(section)
            
            # 合并搜索词（去重）
            for query in result.matched_queries:
                qid = query.get('id')
                if qid and qid not in seen_query_ids:
                    seen_query_ids.add(qid)
                    merged['matched_queries'].append(query)
            
            # 合并来源（去重）
            for source in result.matched_sources:
                sid = source.get('id')
                if sid and sid not in seen_source_ids:
                    seen_source_ids.add(sid)
                    merged['matched_sources'].append(source)
        
        merged['total_nodes'] = (
            len(merged['matched_sections']) +
            len(merged['matched_queries']) +
            len(merged['matched_sources'])
        )
        
        # 生成跨引擎洞察
        merged['cross_engine_insights'] = self._generate_cross_engine_insights(merged)
        
        return merged
    
    def _generate_cross_engine_insights(self, merged: Dict[str, Any]) -> List[str]:
        """生成跨引擎关联洞察"""
        insights = []
        
        # 统计各引擎的段落数
        engine_sections = {}
        for section in merged['matched_sections']:
            engine = section.get('engine', 'unknown')
            engine_sections[engine] = engine_sections.get(engine, 0) + 1
        
        if len(engine_sections) > 1:
            engines = list(engine_sections.keys())
            insights.append(f"跨引擎信息来源: {', '.join(engines)}")
        
        # 统计搜索词的引擎分布
        engine_queries = {}
        for query in merged['matched_queries']:
            engine = query.get('engine', 'unknown')
            if engine not in engine_queries:
                engine_queries[engine] = []
            engine_queries[engine].append(query.get('query_text', ''))
        
        if len(engine_queries) > 1:
            insights.append(f"多引擎搜索视角: {len(engine_queries)} 个引擎提供了相关搜索")
        
        return insights
