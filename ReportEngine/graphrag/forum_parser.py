"""
Forum 日志解析器

解析 forum.log 文件，提取结构化的讨论记录用于构建知识图谱。
日志与 GraphRAG 的关系：仅将主持人/三引擎发言转为结构化节点，
用于补充 Host 总结或跨引擎观点。
"""

from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class ForumEntry:
    """论坛讨论条目"""
    timestamp: str
    speaker: str
    content: str
    
    @property
    def is_host(self) -> bool:
        """是否为主持人发言"""
        return self.speaker.upper() == 'HOST'
    
    @property
    def is_system(self) -> bool:
        """是否为系统消息"""
        return self.speaker.upper() == 'SYSTEM'
    
    @property
    def engine_name(self) -> Optional[str]:
        """获取对应的引擎名称（小写）"""
        speaker_upper = self.speaker.upper()
        if speaker_upper in ['INSIGHT', 'MEDIA', 'QUERY', 'HOST']:
            return speaker_upper.lower()
        return None


class ForumParser:
    """
    Forum 日志解析器
    
    解析 forum.log，提取结构化的讨论记录。
    日志格式: [HH:MM:SS] [SPEAKER] content
    SPEAKER 需属于 VALID_SPEAKERS；非规范行会被忽略，确保图谱不被噪音污染。
    """
    
    # 匹配日志行的正则表达式
    PATTERN = re.compile(r'\[(\d{2}:\d{2}:\d{2})\]\s*\[(\w+)\]\s*(.+)')
    
    # 有效的发言者
    VALID_SPEAKERS = {'INSIGHT', 'MEDIA', 'QUERY', 'HOST', 'SYSTEM'}
    
    def parse(self, forum_logs: str) -> List[ForumEntry]:
        """
        解析 forum.log 内容
        
        Args:
            forum_logs: forum.log 文件内容
            
        Returns:
            ForumEntry 列表
        """
        if not forum_logs:
            return []
        
        entries = []
        
        for line in forum_logs.strip().split('\n'):
            if not line.strip():
                continue
            
            match = self.PATTERN.match(line)
            if match:
                timestamp, speaker, content = match.groups()
                speaker_upper = speaker.upper()
                
                if speaker_upper in self.VALID_SPEAKERS:
                    # 处理转义的换行符
                    content = content.replace('\\n', '\n')
                    
                    entries.append(ForumEntry(
                        timestamp=timestamp,
                        speaker=speaker_upper,
                        content=content
                    ))
        
        return entries
    
    def get_host_insights(self, entries: List[ForumEntry]) -> List[str]:
        """
        提取 Host（主持人）的发言内容
        
        Args:
            entries: ForumEntry 列表
            
        Returns:
            Host 发言内容列表
        """
        return [e.content for e in entries if e.is_host]
    
    def get_engine_entries(self, entries: List[ForumEntry], 
                           engine: str) -> List[ForumEntry]:
        """
        获取指定引擎的发言
        
        Args:
            entries: ForumEntry 列表
            engine: 引擎名称 (insight/media/query/host)
            
        Returns:
            该引擎的 ForumEntry 列表
        """
        engine_upper = engine.upper()
        return [e for e in entries if e.speaker == engine_upper]
    
    def get_summary_by_engine(self, entries: List[ForumEntry]) -> dict:
        """
        按引擎分组统计发言
        
        Args:
            entries: ForumEntry 列表
            
        Returns:
            {engine: [contents]} 字典
        """
        result = {
            'insight': [],
            'media': [],
            'query': [],
            'host': []
        }
        
        for entry in entries:
            engine = entry.engine_name
            if engine and engine in result:
                result[engine].append(entry.content)
        
        return result
    
    def extract_key_points(self, entries: List[ForumEntry], 
                           max_points: int = 10) -> List[str]:
        """
        提取关键观点（优先 Host 发言）
        
        Args:
            entries: ForumEntry 列表
            max_points: 最大提取数量
            
        Returns:
            关键观点列表
        """
        key_points = []
        
        # 优先提取 Host 的发言
        for entry in entries:
            if entry.is_host and not entry.is_system:
                # 提取前 200 字作为摘要
                summary = entry.content[:200]
                if len(entry.content) > 200:
                    summary += '...'
                key_points.append(f"[{entry.speaker}] {summary}")
                
                if len(key_points) >= max_points:
                    break
        
        return key_points
