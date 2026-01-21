"""
GraphRAG 提示词模块

包含查询决策和章节增强的完整提示词定义。
"""

# ================== 查询决策提示词 ==================

GRAPHRAG_QUERY_DECISION_SYSTEM = """你是一个智能舆情分析助手，负责决定如何查询知识图谱以获取生成报告章节所需的信息。

知识图谱包含以下节点类型：
- Topic: 用户查询的主题
- Engine: 四个分析引擎（Insight/Media/Query/Host）
- Section: 各引擎报告的段落章节
- SearchQuery: 引擎执行过的搜索关键词
- Source: 搜索发现的信息来源（URL、标题、内容摘要）

你的任务是根据当前章节的需求，决定查询参数以获取最相关的信息。"""

GRAPHRAG_QUERY_DECISION_USER = """
=== 当前任务 ===
正在生成报告章节: "{chapter_title}"
章节编号: {chapter_id}
章节在模板中的定位: {chapter_role}
目标字数: {target_words}字
章节要点: {chapter_emphasis}

=== 完整报告规划 ===
报告主题: {report_topic}
模板类型: {template_name}
全书章节概览:
{chapters_overview}

=== 知识图谱概览 ===
图谱统计:
- 主题节点: 1个 ({topic_name})
- 引擎节点: {engine_count}个
- 段落节点: {section_count}个
- 搜索词节点: {query_count}个  
- 来源节点: {source_count}个

各引擎段落标题:
{section_titles_by_engine}

搜索关键词样例（前20个）:
{sample_search_queries}

=== 查询历史记录（本章节已执行的查询） ===
{query_history_detail}

=== 请决定查询参数 ===
请输出JSON格式的查询参数：
```json
{{
    "should_query": true/false,
    "keywords": ["关键词1", "关键词2", ...],
    "node_types": ["section", "search_query", "source"],
    "engine_filter": ["insight", "media", "query", "host"],
    "depth": 1-3,
    "reasoning": "选择这些参数的原因，以及期望获取什么信息"
}}
```

注意事项：
1. 仔细查看查询历史，**避免重复查询相同或相似的关键词**
2. 关键词应与当前章节主题紧密相关
3. 如果查询历史已经覆盖了章节所需的主要信息，设置 should_query=false
4. depth建议：1=精确匹配，2=包含关联，3=扩展探索（信息量大但可能有噪音）
5. 可以通过 engine_filter 聚焦特定引擎的分析视角
"""

# ================== 章节增强提示词（GraphRAG 开启时使用） ==================

SYSTEM_PROMPT_CHAPTER_GRAPH_ENHANCEMENT = """
=== GraphRAG 知识图谱增强 ===
本次章节生成已通过知识图谱查询获取了跨引擎的关联信息。
在生成内容时，请特别注意：

1. **跨引擎关联**: graphResults 中包含了来自不同引擎的相关信息，
   请综合利用这些多视角的分析结果，形成更全面的观点。

2. **信息溯源**: 对于重要观点，可以引用 graphResults.matched_sources 
   中的来源信息，增强可信度。

3. **搜索词关联**: graphResults.matched_queries 显示了各引擎为本主题
   执行的相关搜索，这些搜索词本身就是重要的语义线索。

4. **避免重复**: 不同引擎可能有相似的分析，请整合而非重复。
"""

USER_PROMPT_GRAPH_RESULTS_TEMPLATE = """
=== GraphRAG 知识图谱查询结果 ===

**查询轮次**: {query_rounds}次

**匹配的相关段落** (来自其他引擎的相关分析):
{matched_sections}

**相关搜索关键词** (各引擎执行的相关搜索):
{matched_queries}

**相关信息来源** (搜索发现的相关URL和内容):
{matched_sources}

**跨引擎关联洞察**:
{cross_engine_insights}

请在生成本章节时，充分利用以上知识图谱查询结果，
特别是跨引擎的关联信息，以丰富内容的多维度分析。
===

"""


def format_graph_results_for_prompt(graph_results: dict) -> str:
    """
    格式化 GraphRAG 查询结果用于提示词
    
    Args:
        graph_results: 查询结果字典
        
    Returns:
        格式化的字符串
    
    供 ReportAgent 在章节生成前注入 `graph_enhancement_prompt`，
    将多轮查询结果以结构化文本交给章节 LLM，避免直接传递大 JSON。
    """
    if not graph_results:
        return ""
    
    # 格式化段落
    matched_sections = graph_results.get('matched_sections', [])
    sections_text = _format_matched_sections(matched_sections)
    
    # 格式化搜索词
    matched_queries = graph_results.get('matched_queries', [])
    queries_text = _format_matched_queries(matched_queries)
    
    # 格式化来源
    matched_sources = graph_results.get('matched_sources', [])
    sources_text = _format_matched_sources(matched_sources)
    
    # 跨引擎洞察
    insights = graph_results.get('cross_engine_insights', [])
    insights_text = _format_cross_engine_insights(insights)
    
    return USER_PROMPT_GRAPH_RESULTS_TEMPLATE.format(
        query_rounds=graph_results.get('query_rounds', 0),
        matched_sections=sections_text,
        matched_queries=queries_text,
        matched_sources=sources_text,
        cross_engine_insights=insights_text
    )


def _format_matched_sections(sections: list) -> str:
    """格式化匹配的段落"""
    if not sections:
        return "（无匹配段落）"
    
    lines = []
    for s in sections[:10]:  # 限制数量
        engine = s.get('engine', 'unknown')
        title = s.get('title', '未知标题')
        summary = s.get('summary', '')[:100]
        lines.append(f"- [{engine}] {title}: {summary}...")
    
    return "\n".join(lines)


def _format_matched_queries(queries: list) -> str:
    """格式化匹配的搜索词"""
    if not queries:
        return "（无匹配搜索词）"
    
    by_engine = {}
    for q in queries:
        engine = q.get('engine', 'unknown')
        if engine not in by_engine:
            by_engine[engine] = []
        query_text = q.get('query_text', q.get('name', ''))
        if query_text and query_text not in by_engine[engine]:
            by_engine[engine].append(query_text)
    
    lines = []
    for engine, query_list in by_engine.items():
        lines.append(f"- {engine}: {', '.join(query_list[:5])}")
    
    return "\n".join(lines)


def _format_matched_sources(sources: list) -> str:
    """格式化匹配的来源"""
    if not sources:
        return "（无匹配来源）"
    
    lines = []
    for s in sources[:8]:
        title = s.get('title', '未知标题')
        url = s.get('url', '#')
        preview = s.get('preview', '')
        lines.append(f"- [{title}]({url})")
        if preview:
            lines.append(f"  摘要: {preview[:80]}...")
    
    return "\n".join(lines)


def _format_cross_engine_insights(insights: list) -> str:
    """格式化跨引擎洞察"""
    if not insights:
        return "（无跨引擎关联发现）"
    
    return "\n".join([f"- {insight}" for insight in insights[:5]])
