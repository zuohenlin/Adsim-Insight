#!/usr/bin/env python3
"""
生成覆盖全部允许block类型的演示 IR，用于验证 HTML / PDF / Markdown 渲染。

执行后会在 `final_reports/ir` 写入一份带时间戳的 IR，
并分别在 `final_reports/html`、`final_reports/pdf` 与 `final_reports/md`
输出对应的渲染文件。
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# 允许直接以脚本形式运行
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ReportEngine.core import DocumentComposer
from ReportEngine.ir import IRValidator
from ReportEngine.ir.schema import ENGINE_AGENT_TITLES
from ReportEngine.renderers import HTMLRenderer, MarkdownRenderer, PDFRenderer
from ReportEngine.utils.config import settings


def build_inline_marks_demo() -> dict:
    """生成覆盖全部内联标记的 paragraph block。"""
    return {
        "type": "paragraph",
        "inlines": [
            {"text": "这一段覆盖全部内联标记："},
            {"text": "粗体", "marks": [{"type": "bold"}]},
            {"text": " / 斜体", "marks": [{"type": "italic"}]},
            {"text": " / 下划线", "marks": [{"type": "underline"}]},
            {"text": " / 删除线", "marks": [{"type": "strike"}]},
            {"text": " / 代码", "marks": [{"type": "code"}]},
            {
                "text": " / 链接",
                "marks": [
                    {
                        "type": "link",
                        "href": "https://example.com/demo",
                        "title": "示例链接",
                    }
                ],
            },
            {"text": " / 颜色", "marks": [{"type": "color", "value": "#c0392b"}]},
            {
                "text": " / 字体",
                "marks": [
                    {
                        "type": "font",
                        "family": "Georgia, serif",
                        "size": "15px",
                        "weight": "600",
                    }
                ],
            },
            {"text": " / 高亮", "marks": [{"type": "highlight"}]},
            {"text": " / 下标", "marks": [{"type": "subscript"}]},
            {"text": " / 上标", "marks": [{"type": "superscript"}]},
            {"text": " / 行内公式", "marks": [{"type": "math", "value": "E=mc^2"}]},
            {"text": "。"},
        ],
    }


def build_widget_block() -> dict:
    """构造一个合法的 Chart.js widget block。"""
    return {
        "type": "widget",
        "widgetId": "demo-volume-trend",
        "widgetType": "chart.js/line",
        "props": {
            "type": "line",
            "options": {
                "responsive": True,
                "plugins": {"legend": {"position": "bottom"}},
                "scales": {"y": {"title": {"display": True, "text": "提及量"}}},
            },
        },
        "data": {
            "labels": ["T0", "T0+6h", "T0+12h", "T0+18h", "T0+24h"],
            "datasets": [
                {
                    "label": "主流媒体",
                    "data": [12, 18, 23, 30, 26],
                    "borderColor": "#2980b9",
                    "backgroundColor": "rgba(41,128,185,0.18)",
                    "tension": 0.25,
                    "fill": False,
                },
                {
                    "label": "社交平台",
                    "data": [8, 10, 15, 28, 40],
                    "borderColor": "#c0392b",
                    "backgroundColor": "rgba(192,57,43,0.2)",
                    "tension": 0.35,
                    "fill": False,
                },
            ],
        },
    }


def build_chapters() -> list[dict]:
    """构造覆盖所有 block 类型的章节列表。"""
    inline_demo = build_inline_marks_demo()

    bullet_list = {
        "type": "list",
        "listType": "bullet",
        "items": [
            [
                {
                    "type": "paragraph",
                    "inlines": [{"text": "社交媒体热度在 48 小时内翻倍"}],
                }
            ],
            [
                {
                    "type": "paragraph",
                    "inlines": [{"text": "主流媒体报道集中在早间时段"}],
                },
                {
                    "type": "list",
                    "listType": "ordered",
                    "items": [
                        [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "07:00-09:00：首轮报道"}],
                            }
                        ],
                        [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "10:00-12:00：评论扩散"}],
                            }
                        ],
                    ],
                },
            ],
            [
                {
                    "type": "paragraph",
                    "inlines": [{"text": "地方政务号开始回应并同步线下通稿"}],
                }
            ],
        ],
    }

    task_list = {
        "type": "list",
        "listType": "task",
        "items": [
            [
                {
                    "type": "paragraph",
                    "inlines": [{"text": "跟踪权威辟谣素材是否上线"}],
                }
            ],
            [
                {
                    "type": "paragraph",
                    "inlines": [{"text": "监测新增关联关键词与长尾问题"}],
                }
            ],
            [
                {
                    "type": "paragraph",
                    "inlines": [{"text": "准备 FAQ 供客服统一答复"}],
                }
            ],
        ],
    }

    table_block = {
        "type": "table",
        "caption": "核心信源与传播路径",
        "zebra": True,
        "colgroup": [{"width": "22%"}, {"width": "38%"}, {"width": "40%"}],
        "rows": [
            {
                "cells": [
                    {
                        "align": "center",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "时间节点", "marks": [{"type": "bold"}]}],
                            }
                        ],
                    },
                    {
                        "align": "center",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "事件内容", "marks": [{"type": "bold"}]}],
                            }
                        ],
                    },
                    {
                        "align": "center",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "主要渠道", "marks": [{"type": "bold"}]}],
                            }
                        ],
                    },
                ]
            },
            {
                "cells": [
                    {"blocks": [{"type": "paragraph", "inlines": [{"text": "T0"}]}]},
                    {
                        "blocks": [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "线下冲突视频首次上传"}],
                            }
                        ]
                    },
                    {
                        "blocks": [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "短视频平台 / 私聊转发"}],
                            }
                        ]
                    },
                ]
            },
            {
                "cells": [
                    {"blocks": [{"type": "paragraph", "inlines": [{"text": "T0+6h"}]}]},
                    {
                        "blocks": [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "登上热搜，出现二次剪辑"}],
                            }
                        ]
                    },
                    {
                        "blocks": [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "微博 / 朋友圈"}],
                            }
                        ]
                    },
                ]
            },
            {
                "cells": [
                    {"blocks": [{"type": "paragraph", "inlines": [{"text": "T0+18h"}]}]},
                    {
                        "blocks": [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "官方回应并发布事实澄清"}],
                            }
                        ]
                    },
                    {
                        "blocks": [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "政务号 / 新闻客户端"}],
                            }
                        ]
                    },
                ]
            },
            {
                "cells": [
                    {"blocks": [{"type": "paragraph", "inlines": [{"text": "T0+24h"}]}]},
                    {
                        "blocks": [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "专家解读，舆论重心转向责任归属"}],
                            }
                        ]
                    },
                    {
                        "blocks": [
                            {
                                "type": "paragraph",
                                "inlines": [{"text": "视频号直播 / 行业社群"}],
                            }
                        ]
                    },
                ]
            },
        ],
    }

    blockquote_block = {
        "type": "blockquote",
        "variant": "accent",
        "blocks": [
            {
                "type": "paragraph",
                "inlines": [{"text": "“公众最关心的信息是真相与责任边界。”"}],
            },
            {
                "type": "paragraph",
                "inlines": [{"text": "—— 模拟引用，验证引用块样式"}],
            },
        ],
    }

    engine_quote_block = {
        "type": "engineQuote",
        "engine": "insight",
        "title": ENGINE_AGENT_TITLES["insight"],
        "blocks": [
            {
                "type": "paragraph",
                "inlines": [
                    {
                        "text": "模型认为 24 小时内保持回应频次，可避免信息真空。",
                        "marks": [{"type": "bold"}],
                    }
                ],
            },
            {
                "type": "paragraph",
                "inlines": [
                    {"text": "建议同时准备简短 FAQ，便于多渠道统一口径。"}
                ],
            },
        ],
    }

    swot_block = {
        "type": "swotTable",
        "title": "舆论场 SWOT 速览",
        "summary": "覆盖当前情绪分布、潜在风险与机会。",
        "strengths": [
            {"title": "官方快速响应", "detail": "首条澄清视频 3 小时内上线"},
            {"title": "同城媒体配合", "impact": "高", "score": 8},
        ],
        "weaknesses": [
            {"title": "早期谣言存量大", "detail": "相关转发仍占 30%"},
            "外部专家尚未统一口径",
        ],
        "opportunities": [
            {
                "title": "社区共建讨论",
                "detail": "自发组织“辟谣志愿者”话题，情绪正向",
            },
            {"title": "公益合作窗口", "impact": "中"},
        ],
        "threats": [
            {"title": "跨平台剪辑继续发酵", "impact": "高", "score": 9},
            {"title": "个别自媒体煽动情绪", "evidence": "存在地域标签化倾向"},
        ],
    }

    pest_block = {
        "type": "pestTable",
        "title": "宏观环境脉冲扫描（PEST）",
        "summary": "模拟四大维度的外部约束与机会，验证 pestTable 的渲染样式。",
        "political": [
            {
                "title": "地方条例征求意见",
                "detail": "短视频发布需实名溯源，平台合规沟通窗口期开启",
                "trend": "正面利好",
                "impact": 7,
            },
            {
                "title": "监管关注情绪煽动",
                "detail": "对夸大矛盾的账号重点巡查，舆论阈值下调",
                "trend": "持续观察",
                "impact": 6,
            },
        ],
        "economic": [
            {
                "title": "周边商户营收波动",
                "detail": "客流短期下滑 12%，但直播带货订单上升",
                "trend": "中性",
                "impact": 5,
            },
            {
                "title": "品牌赞助谨慎",
                "detail": "赞助延期观察声誉风险，对官宣节奏有压力",
                "trend": "不确定",
                "impact": 4,
            },
        ],
        "social": [
            {
                "title": "核心群体情绪分化",
                "detail": "本地居民关注安全，外地游客关注体验与退款",
                "trend": "负面影响",
                "impact": 8,
            },
            {
                "title": "高校社群自发求证",
                "detail": "校媒与学生会组织“以图搜图”科普贴，情绪趋稳",
                "trend": "正面利好",
                "impact": 6,
            },
        ],
        "technological": [
            {
                "title": "AI 生成内容被混入",
                "detail": "局部画面被放大后再传播，需水印溯源工具辅助鉴伪",
                "trend": "负面影响",
                "impact": 7,
            },
            {
                "title": "多模态检索上线",
                "detail": "平台试行“视频反诈”模型，自动提示剪辑痕迹",
                "trend": "正面利好",
                "impact": 5,
            },
        ],
    }

    callout_block = {
        "type": "callout",
        "tone": "warning",
        "title": "排版边界提示",
        "blocks": [
            {
                "type": "paragraph",
                "inlines": [
                    {"text": "callout 内部仅放轻量内容，超出部分会自动溢出到外层。"}
                ],
            },
            {
                "type": "list",
                "listType": "bullet",
                "items": [
                    [
                        {
                            "type": "paragraph",
                            "inlines": [{"text": "支持嵌套列表 / 表格 / 数学公式"}],
                        }
                    ],
                    [
                        {
                            "type": "paragraph",
                            "inlines": [{"text": "可在这里放置提醒或操作步骤"}],
                        }
                    ],
                ],
            },
        ],
    }

    code_block = {
        "type": "code",
        "lang": "json",
        "caption": "演示代码块",
        "content": '{\n  "event": "热点示例",\n  "topic": "公共事件",\n  "status": "monitoring"\n}',
    }

    math_block = {
        "type": "math",
        "latex": r"E = mc^2",
        "displayMode": True,
    }

    figure_block = {
        "type": "figure",
        "img": {
            "src": "https://dummyimage.com/600x320/eeeeee/333333&text=Placeholder",
            "alt": "占位示意图",
            "width": 600,
            "height": 320,
        },
        "caption": "图像外链被替换为友好提示，可验证 figure 占位效果。",
        "responsive": True,
    }

    widget_block = build_widget_block()
    stacked_bar_chart_block = {
        "type": "widget",
        "widgetId": "demo-stacked-sentiment",
        "widgetType": "chart.js/bar",
        "props": {
            "type": "bar",
            "options": {
                "responsive": True,
                "plugins": {"legend": {"position": "bottom"}},
                "scales": {
                    "x": {"stacked": True},
                    "y": {"stacked": True, "title": {"display": True, "text": "信息量"}},
                },
            },
        },
        "data": {
            "labels": ["周一", "周二", "周三", "周四", "周五"],
            "datasets": [
                {"label": "正向", "data": [18, 22, 24, 19, 16], "backgroundColor": "#27ae60"},
                {"label": "中性", "data": [22, 20, 18, 21, 23], "backgroundColor": "#f39c12"},
                {"label": "负向", "data": [12, 14, 10, 9, 11], "backgroundColor": "#c0392b"},
            ],
        },
    }
    horizontal_bar_chart_block = {
        "type": "widget",
        "widgetId": "demo-horizontal-voice",
        "widgetType": "chart.js/bar",
        "props": {
            # 通过 indexAxis 切换横向柱状图
            "type": "bar",
            "options": {
                "indexAxis": "y",
                "plugins": {"legend": {"position": "right"}},
                "scales": {"x": {"title": {"display": True, "text": "提及量(万)"}}},
            },
        },
        "data": {
            "labels": ["微博", "短视频", "社区论坛", "新闻客户端"],
            "datasets": [
                {
                    "label": "声量对比",
                    "data": [42, 58, 27, 36],
                    "backgroundColor": ["#2ecc71", "#3498db", "#9b59b6", "#f39c12"],
                }
            ],
        },
    }
    pie_chart_block = {
        "type": "widget",
        "widgetId": "demo-stance-pie",
        "widgetType": "chart.js/pie",
        "props": {
            "type": "pie",
            "options": {"plugins": {"legend": {"position": "bottom"}}},
        },
        "data": {
            "labels": ["支持", "中立", "质疑"],
            "datasets": [
                {
                    "label": "立场分布",
                    "data": [36, 28, 21],
                    "backgroundColor": ["#27ae60", "#f1c40f", "#c0392b"],
                }
            ],
        },
    }
    doughnut_chart_block = {
        "type": "widget",
        "widgetId": "demo-sentiment-share",
        "widgetType": "chart.js/doughnut",
        "props": {
            "type": "doughnut",
            "options": {"plugins": {"legend": {"position": "right"}, "tooltip": {"enabled": True}}},
        },
        "data": {
            "labels": ["政策", "经济", "社会", "技术"],
            "datasets": [
                {
                    "label": "关注度占比",
                    "data": [24, 30, 28, 18],
                    "backgroundColor": ["#8e44ad", "#16a085", "#e67e22", "#2980b9"],
                    "hoverOffset": 6,
                }
            ],
        },
    }
    radar_chart_block = {
        "type": "widget",
        "widgetId": "demo-response-radar",
        "widgetType": "chart.js/radar",
        "props": {
            "type": "radar",
            "options": {
                "plugins": {"legend": {"position": "top"}},
                "scales": {"r": {"beginAtZero": True, "max": 100}},
            },
        },
        "data": {
            "labels": ["透明度", "响应速度", "一致性", "互动度", "信息量"],
            "datasets": [
                {
                    "label": "官方渠道",
                    "data": [78, 88, 82, 66, 91],
                    "backgroundColor": "rgba(46,204,113,0.15)",
                    "borderColor": "#2ecc71",
                    "pointBackgroundColor": "#27ae60",
                },
                {
                    "label": "民间讨论",
                    "data": [64, 72, 58, 74, 63],
                    "backgroundColor": "rgba(52,152,219,0.12)",
                    "borderColor": "#3498db",
                    "pointBackgroundColor": "#2980b9",
                },
            ],
        },
    }
    polar_area_chart_block = {
        "type": "widget",
        "widgetId": "demo-channel-polar",
        "widgetType": "chart.js/polarArea",
        "props": {"type": "polarArea"},
        "data": {
            "labels": ["短视频", "微博", "社区论坛", "新闻客户端", "线下反馈"],
            "datasets": [
                {
                    "label": "渠道渗透度",
                    "data": [62, 54, 38, 45, 28],
                    "backgroundColor": [
                        "rgba(231,76,60,0.65)",
                        "rgba(142,68,173,0.6)",
                        "rgba(52,152,219,0.55)",
                        "rgba(46,204,113,0.55)",
                        "rgba(241,196,15,0.6)",
                    ],
                }
            ],
        },
    }
    scatter_chart_block = {
        "type": "widget",
        "widgetId": "demo-correlation-scatter",
        "widgetType": "chart.js/scatter",
        "props": {
            "type": "scatter",
            "options": {
                "plugins": {"legend": {"position": "bottom"}},
                "scales": {
                    "x": {"title": {"display": True, "text": "情绪极性"}, "min": -1, "max": 1},
                    "y": {"title": {"display": True, "text": "互动量"}, "beginAtZero": True},
                },
            },
        },
        "data": {
            "datasets": [
                {
                    "label": "帖子散点",
                    "data": [
                        {"x": -0.65, "y": 120},
                        {"x": -0.25, "y": 190},
                        {"x": 0.05, "y": 260},
                        {"x": 0.42, "y": 340},
                        {"x": 0.78, "y": 410},
                    ],
                    "backgroundColor": "rgba(52,152,219,0.7)",
                }
            ],
        },
    }
    bubble_chart_block = {
        "type": "widget",
        "widgetId": "demo-impact-bubble",
        "widgetType": "chart.js/bubble",
        "props": {
            "type": "bubble",
            "options": {
                "plugins": {"legend": {"position": "bottom"}},
                "scales": {
                    "x": {"title": {"display": True, "text": "曝光量 (万)"}, "beginAtZero": True},
                    "y": {"title": {"display": True, "text": "情绪强度"}, "min": -100, "max": 100},
                },
            },
        },
        "data": {
            "datasets": [
                {
                    "label": "渠道分布",
                    "data": [
                        {"x": 8, "y": 35, "r": 12},
                        {"x": 12, "y": -28, "r": 10},
                        {"x": 18, "y": 22, "r": 14},
                        {"x": 25, "y": 48, "r": 16},
                        {"x": 6, "y": -12, "r": 8},
                    ],
                    "backgroundColor": "rgba(192,57,43,0.55)",
                    "borderColor": "#c0392b",
                }
            ],
        },
    }

    chapter_1 = {
        "chapterId": "S1",
        "title": "封面与目录",
        "anchor": "overview",
        "order": 10,
        "blocks": [
            {"type": "heading", "level": 2, "text": "一、封面与目录", "anchor": "overview"},
            {
                "type": "paragraph",
                "inlines": [
                    {
                        "text": "模拟社会公共热点事件的摘要，便于快速确认排版与字体效果。",
                    }
                ],
            },
            inline_demo,
            {
                "type": "kpiGrid",
                "items": [
                    {"label": "24h提及量", "value": "98K", "delta": "+41%", "deltaTone": "up"},
                    {"label": "正向占比", "value": "32%", "delta": "+5pp", "deltaTone": "up"},
                    {"label": "负向占比", "value": "18%", "delta": "-3pp", "deltaTone": "down"},
                    {"label": "高频渠道", "value": "短视频 / 微博"},
                ],
                "cols": 4,
            },
            {"type": "toc"},
            {"type": "hr"},
        ],
    }

    chapter_2 = {
        "chapterId": "S2",
        "title": "块类型演示",
        "anchor": "blocks-showcase",
        "order": 20,
        "blocks": [
            {
                "type": "heading",
                "level": 2,
                "text": "二、块类型演示",
                "anchor": "blocks-showcase",
            },
            {
                "type": "paragraph",
                "inlines": [
                    {
                        "text": "以下内容逐一覆盖 paragraph/list/table/swot/pest/widget 等全部块类型。",
                    }
                ],
            },
            {
                "type": "heading",
                "level": 3,
                "text": "2.1 列表与表格",
                "anchor": "lists-and-tables",
            },
            bullet_list,
            task_list,
            table_block,
            {
                "type": "heading",
                "level": 3,
                "text": "2.2 图表组件演示",
                "anchor": "charts-demo",
            },
            {
                "type": "paragraph",
                "inlines": [
                    {
                        "text": "折线 / 柱状（含横向、堆叠）/ 饼图 / 圆环 / 雷达 / 极区 / 散点 / 气泡等多类型图表，用于验证 Chart.js 兼容性。",
                    }
                ],
            },
            widget_block,
            stacked_bar_chart_block,
            horizontal_bar_chart_block,
            pie_chart_block,
            doughnut_chart_block,
            radar_chart_block,
            polar_area_chart_block,
            scatter_chart_block,
            bubble_chart_block,
            {
                "type": "heading",
                "level": 3,
                "text": "2.3 高阶块与富媒体",
                "anchor": "advanced-blocks",
            },
            blockquote_block,
            callout_block,
            engine_quote_block,
            swot_block,
            pest_block,
            code_block,
            math_block,
            figure_block,
            {
                "type": "hr",
                "variant": "dashed",
            },
            {
                "type": "paragraph",
                "align": "justify",
                "inlines": [
                    {
                        "text": "本章节的 inline math 兜底验证：",
                    },
                    {"text": "p(t)=p_0 e^{\\lambda t}", "marks": [{"type": "math"}]},
                    {"text": "；以上覆盖所有允许块及标记。"},
                ],
            },
        ],
    }

    return [chapter_1, chapter_2]


def validate_chapters(chapters: list[dict]) -> None:
    """使用 IRValidator 校验章节结构，发现错误时抛出异常。"""
    validator = IRValidator()
    for chapter in chapters:
        ok, errors = validator.validate_chapter(chapter)
        if not ok:
            raise ValueError(f"{chapter.get('chapterId', 'unknown')} 校验失败: {errors}")


def render_and_save(document_ir: dict, timestamp: str) -> tuple[Path, Path, Path, Path]:
    """将 IR 保存为 JSON，并渲染 HTML / PDF / Markdown，返回四个路径。"""
    ir_dir = Path(settings.DOCUMENT_IR_OUTPUT_DIR)
    html_dir = Path(settings.OUTPUT_DIR) / "html"
    pdf_dir = Path(settings.OUTPUT_DIR) / "pdf"
    md_dir = Path(settings.OUTPUT_DIR) / "md"
    ir_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)

    ir_path = ir_dir / f"report_ir_all_blocks_demo_{timestamp}.json"
    ir_path.write_text(json.dumps(document_ir, ensure_ascii=False, indent=2), encoding="utf-8")

    html_renderer = HTMLRenderer()
    html_content = html_renderer.render(document_ir)
    html_path = html_dir / f"report_html_all_blocks_demo_{timestamp}.html"
    html_path.write_text(html_content, encoding="utf-8")

    pdf_renderer = PDFRenderer()
    pdf_path = pdf_dir / f"report_pdf_all_blocks_demo_{timestamp}.pdf"
    pdf_renderer.render_to_pdf(document_ir, pdf_path)

    md_renderer = MarkdownRenderer()
    md_content = md_renderer.render(document_ir, ir_file_path=str(ir_path))
    md_path = md_dir / f"report_md_all_blocks_demo_{timestamp}.md"
    md_path.write_text(md_content, encoding="utf-8")

    return ir_path, html_path, pdf_path, md_path


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_id = f"all-blocks-demo-{timestamp}"
    metadata = {
        "title": "社会公共热点事件渲染测试",
        "subtitle": "覆盖全部 IR 块类型的示例数据，含多种图表与 PEST 演示",
        "query": "公共事件渲染能力自检 / Chart & PEST",
        "toc": {"title": "目录", "depth": 3},
        "hero": {
            "summary": "用于验证 Report Engine 在 HTML / PDF 渲染时对各类区块、Chart.js 组件与 PEST 模块的兼容性。",
            "kpis": [
                {"label": "示例块数量", "value": "20+", "delta": "含 PEST", "tone": "up"},
                {"label": "图表数", "value": "7", "delta": "新增多类型", "tone": "neutral"},
            ],
            "highlights": ["覆盖全部 block", "含行内/块级公式", "Chart.js 多类型", "PEST + SWOT"],
            "actions": ["重新生成", "导出 PDF"],
        },
    }

    chapters = build_chapters()
    validate_chapters(chapters)

    composer = DocumentComposer()
    document_ir = composer.build_document(report_id, metadata, chapters)

    ir_path, html_path, pdf_path, md_path = render_and_save(document_ir, timestamp)

    print("✅ 演示 IR 生成完成")
    print(f"IR:   {ir_path}")
    print(f"HTML: {html_path}")
    print(f"PDF:  {pdf_path}")
    print(f"MD:   {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
