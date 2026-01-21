"""
专为 AI Agent 设计的舆情搜索工具集 (支持 DuckDuckGo / Tavily)

版本: 2.0
最后更新: 2026-01-21

本模块提供统一的搜索接口，支持免费的 DuckDuckGo 和付费的 Tavily。
DuckDuckGo 模式无需 API Key，完全免费且无额度限制。

主要工具:
- basic_search_news: 执行标准、快速的通用新闻搜索。
- deep_search_news: 对主题进行深度搜索。
- search_news_last_24_hours: 获取24小时内的最新动态。
- search_news_last_week: 获取过去一周的主要报道。
- search_images_for_news: 查找与新闻主题相关的图片。
- search_news_by_date: 在指定的历史日期范围内搜索。
"""

import os
import sys
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# 添加 utils 目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
utils_dir = os.path.join(root_dir, 'utils')
if utils_dir not in sys.path:
    sys.path.append(utils_dir)

from retry_helper import with_graceful_retry, SEARCH_API_RETRY_CONFIG

# 尝试导入搜索引擎客户端
HAS_DDG = False
HAS_TAVILY = False

try:
    from duckduckgo_search import DDGS
    HAS_DDG = True
except ImportError:
    pass

try:
    from tavily import TavilyClient
    HAS_TAVILY = True
except ImportError:
    pass

# --- 1. 数据结构定义 ---

@dataclass
class SearchResult:
    """网页搜索结果数据类"""
    title: str
    url: str
    content: str
    score: Optional[float] = None
    raw_content: Optional[str] = None
    published_date: Optional[str] = None
    source: str = "unknown"

@dataclass
class ImageResult:
    """图片搜索结果数据类"""
    url: str
    description: Optional[str] = None
    source: str = "unknown"

@dataclass
class TavilyResponse:
    """统一的搜索响应格式（保持向后兼容）"""
    query: str
    answer: Optional[str] = None
    results: List[SearchResult] = field(default_factory=list)
    images: List[ImageResult] = field(default_factory=list)
    response_time: Optional[float] = None
    engine: str = "unknown"


# --- 2. 搜索引擎实现 ---

class BaseSearchEngine:
    """搜索引擎基类，定义标准接口"""
    def search(self, query: str, **kwargs) -> TavilyResponse:
        raise NotImplementedError


class DuckDuckGoSearchEngine(BaseSearchEngine):
    """DuckDuckGo 免费搜索引擎实现"""
    
    def __init__(self):
        if not HAS_DDG:
            raise ImportError("请先安装 duckduckgo-search>=5.0.0: pip install duckduckgo-search")
        self._ddgs = DDGS()
    
    @with_graceful_retry(SEARCH_API_RETRY_CONFIG, default_return=TavilyResponse(query="搜索失败", engine="duckduckgo"))
    def search(self, query: str, **kwargs) -> TavilyResponse:
        start_time = time.time()
        results = []
        images = []
        
        # 提取参数
        max_results = kwargs.get('max_results', 10)
        time_range = kwargs.get('time_range', None)  # 'd', 'w', 'm'
        include_images = kwargs.get('include_images', False)
        
        # 映射时间参数
        ddg_timelimit = None
        if time_range == 'd':
            ddg_timelimit = 'd'
        elif time_range == 'w':
            ddg_timelimit = 'w'
        elif time_range == 'm':
            ddg_timelimit = 'm'
        
        try:
            # 执行文本搜索
            ddg_results = self._ddgs.text(
                keywords=query,
                region='wt-wt',
                safesearch='moderate',
                timelimit=ddg_timelimit,
                max_results=max_results
            )
            
            for r in ddg_results:
                results.append(SearchResult(
                    title=r.get('title', ''),
                    url=r.get('href', ''),
                    content=r.get('body', ''),
                    source='duckduckgo',
                    published_date=None  # DDG 不直接返回日期
                ))
            
            # 如果请求图片
            if include_images:
                ddg_images = self._ddgs.images(
                    keywords=query,
                    region='wt-wt',
                    safesearch='moderate',
                    max_results=5
                )
                for img in ddg_images:
                    images.append(ImageResult(
                        url=img.get('image', ''),
                        description=img.get('title', ''),
                        source='duckduckgo'
                    ))
                    
        except Exception as e:
            print(f"DuckDuckGo 搜索出错: {e}")
            raise e
            
        elapsed = time.time() - start_time
        return TavilyResponse(
            query=query,
            results=results,
            images=images,
            response_time=elapsed,
            engine='duckduckgo'
        )


class TavilySearchEngine(BaseSearchEngine):
    """Tavily 付费搜索引擎实现"""
    
    def __init__(self, api_key: str):
        if not HAS_TAVILY:
            raise ImportError("请先安装 tavily-python: pip install tavily-python")
        self._client = TavilyClient(api_key=api_key)
    
    @with_graceful_retry(SEARCH_API_RETRY_CONFIG, default_return=TavilyResponse(query="搜索失败", engine="tavily"))
    def search(self, query: str, **kwargs) -> TavilyResponse:
        start_time = time.time()
        
        # 准备参数
        api_params = {
            'query': query,
            'search_depth': kwargs.get('search_depth', "basic"),
            'include_images': kwargs.get('include_images', False),
            'include_answer': kwargs.get('include_answer', False),
            'max_results': kwargs.get('max_results', 5),
            'topic': 'general'
        }
        
        # 处理时间范围
        if 'time_range' in kwargs:
            api_params['time_range'] = kwargs['time_range']
        if 'start_date' in kwargs:
            api_params['start_date'] = kwargs['start_date']
        if 'end_date' in kwargs:
            api_params['end_date'] = kwargs['end_date']
            
        response_dict = self._client.search(**api_params)
        
        search_results = [
            SearchResult(
                title=item.get('title'),
                url=item.get('url'),
                content=item.get('content'),
                score=item.get('score'),
                raw_content=item.get('raw_content'),
                published_date=item.get('published_date'),
                source='tavily'
            ) for item in response_dict.get('results', [])
        ]
        
        image_results = [
            ImageResult(
                url=item.get('url'), 
                description=item.get('description'),
                source='tavily'
            ) for item in response_dict.get('images', [])
        ]

        elapsed = time.time() - start_time
        return TavilyResponse(
            query=response_dict.get('query'), 
            answer=response_dict.get('answer'),
            results=search_results, 
            images=image_results,
            response_time=response_dict.get('response_time', elapsed),
            engine='tavily'
        )


# --- 3. 统一代理类 (兼容原接口) ---

class TavilyNewsAgency:
    """
    统一搜索代理，保持类名兼容性。
    根据配置动态选择后端 (DuckDuckGo 或 Tavily)。
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化客户端。
        优先读取环境变量 SEARCH_TOOL_TYPE (DuckDuckGo/Tavily)
        如果无 API Key 且选择 Tavily，则自动降级为 DuckDuckGo
        """
        self.engine_type = os.getenv("SEARCH_TOOL_TYPE", "DuckDuckGo")
        self._engine = None
        
        if self.engine_type.lower() == "duckduckgo":
            print("正在初始化 DuckDuckGo 免费搜索引擎...")
            try:
                self._engine = DuckDuckGoSearchEngine()
            except ImportError as e:
                print(f"DuckDuckGo 初始化失败: {e}")
                print("尝试回退到 Tavily...")
                self.engine_type = "Tavily"
        
        if self.engine_type.lower() in ["tavily", "anspire"]:
            if api_key is None:
                api_key = os.getenv("TAVILY_API_KEY")
            
            if not api_key:
                print("未找到 Tavily API Key，自动降级为 DuckDuckGo 免费搜索...")
                try:
                    self._engine = DuckDuckGoSearchEngine()
                    self.engine_type = "DuckDuckGo"
                except ImportError:
                    raise ValueError("无法初始化搜索引擎：未提供 API Key 且无法使用 DuckDuckGo")
            else:
                try:
                    self._engine = TavilySearchEngine(api_key)
                except ImportError:
                    print("Tavily 库未安装，降级为 DuckDuckGo...")
                    self._engine = DuckDuckGoSearchEngine()
                    self.engine_type = "DuckDuckGo"

        if self._engine is None:
            # 默认尝试 DDG
            self._engine = DuckDuckGoSearchEngine()
            self.engine_type = "DuckDuckGo"
        
        print(f"搜索引擎已初始化: {self.engine_type}")

    def _search_internal(self, **kwargs) -> TavilyResponse:
        """内部搜索方法"""
        return self._engine.search(**kwargs)

    # --- Agent 可用的工具方法 ---

    def basic_search_news(self, query: str, max_results: int = 7) -> TavilyResponse:
        """
        【工具】基础新闻搜索: 执行一次标准、快速的新闻搜索。
        这是最常用的通用搜索工具。
        """
        print(f"--- TOOL: 基础新闻搜索 (query: {query}) ---")
        return self._search_internal(
            query=query,
            max_results=max_results,
            search_depth="basic",
            include_answer=False
        )

    def deep_search_news(self, query: str) -> TavilyResponse:
        """
        【工具】深度新闻分析: 对一个主题进行最全面、最深入的搜索。
        返回最多20条最相关的新闻结果。
        """
        print(f"--- TOOL: 深度新闻分析 (query: {query}) ---")
        return self._search_internal(
            query=query, 
            search_depth="advanced", 
            max_results=20, 
            include_answer=True
        )

    def search_news_last_24_hours(self, query: str) -> TavilyResponse:
        """
        【工具】搜索24小时内新闻: 获取关于某个主题的最新动态。
        """
        print(f"--- TOOL: 搜索24小时内新闻 (query: {query}) ---")
        return self._search_internal(query=query, time_range='d', max_results=10)

    def search_news_last_week(self, query: str) -> TavilyResponse:
        """
        【工具】搜索本周新闻: 获取关于某个主题过去一周内的主要新闻报道。
        """
        print(f"--- TOOL: 搜索本周新闻 (query: {query}) ---")
        return self._search_internal(query=query, time_range='w', max_results=10)

    def search_images_for_news(self, query: str) -> TavilyResponse:
        """
        【工具】查找新闻图片: 搜索与某个新闻主题相关的图片。
        """
        print(f"--- TOOL: 查找新闻图片 (query: {query}) ---")
        return self._search_internal(
            query=query, 
            include_images=True, 
            max_results=5
        )

    def search_news_by_date(self, query: str, start_date: str, end_date: str) -> TavilyResponse:
        """
        【工具】按指定日期范围搜索新闻: 在一个明确的历史时间段内搜索新闻。
        日期格式: 'YYYY-MM-DD'
        注意: DuckDuckGo 不支持精确日期范围，将使用近似时间过滤。
        """
        print(f"--- TOOL: 按日期范围搜索新闻 (query: {query}, from: {start_date}, to: {end_date}) ---")
        
        if self.engine_type.lower() == "duckduckgo":
            # DDG 不支持精确日期范围，使用 'w' 或 'm' 近似
            print("注意: DuckDuckGo 不支持精确日期范围，使用近似时间过滤")
            return self._search_internal(query=query, time_range='m', max_results=15)
        else:
            return self._search_internal(
                query=query, 
                start_date=start_date, 
                end_date=end_date, 
                max_results=15
            )


# --- 4. 测试与使用示例 ---

def print_response_summary(response: TavilyResponse):
    """简化的打印函数，用于展示测试结果"""
    if not response or not response.query:
        print("未能获取有效响应。")
        return
        
    print(f"\n查询: '{response.query}' | 引擎: {response.engine} | 耗时: {response.response_time:.2f}s")
    if response.answer:
        print(f"AI摘要: {response.answer[:120]}...")
    print(f"找到 {len(response.results)} 条网页, {len(response.images)} 张图片。")
    if response.results:
        first_result = response.results[0]
        date_info = f"(发布于: {first_result.published_date})" if first_result.published_date else ""
        print(f"第一条结果: {first_result.title} {date_info}")
    print("-" * 60)


if __name__ == "__main__":
    try:
        # 初始化搜索代理（自动选择引擎）
        agency = TavilyNewsAgency()

        # 测试基础搜索
        response1 = agency.basic_search_news(query="人工智能最新进展", max_results=5)
        print_response_summary(response1)

        # 测试24小时内新闻
        response2 = agency.search_news_last_24_hours(query="科技新闻")
        print_response_summary(response2)

        # 测试图片搜索
        response3 = agency.search_images_for_news(query="太空探索")
        print_response_summary(response3)

    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()