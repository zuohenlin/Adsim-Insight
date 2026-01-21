#!/usr/bin/env python3
"""
PDF导出工具 - 使用Python直接生成PDF，无乱码

用法:
    python ReportEngine/scripts/export_to_pdf.py <报告IR JSON文件> [输出PDF路径]

示例:
    python ReportEngine/scripts/export_to_pdf.py final_reports/ir/report_ir_xxx.json output.pdf
    python ReportEngine/scripts/export_to_pdf.py final_reports/ir/report_ir_xxx.json
"""

import sys
import json
from pathlib import Path
from loguru import logger

from ReportEngine.renderers import PDFRenderer


def export_to_pdf(ir_json_path: str, output_pdf_path: str = None):
    """
    从IR JSON文件生成PDF

    参数:
        ir_json_path: Document IR JSON文件路径
        output_pdf_path: 输出PDF路径（可选，默认为同名.pdf）
    """
    ir_path = Path(ir_json_path)

    if not ir_path.exists():
        logger.error(f"文件不存在: {ir_path}")
        return False

    # 读取IR数据
    logger.info(f"读取报告: {ir_path}")
    with open(ir_path, 'r', encoding='utf-8') as f:
        document_ir = json.load(f)

    # 确定输出路径
    if output_pdf_path is None:
        output_pdf_path = ir_path.parent / f"{ir_path.stem}.pdf"
    else:
        output_pdf_path = Path(output_pdf_path)

    # 生成PDF
    logger.info(f"开始生成PDF...")
    renderer = PDFRenderer()

    try:
        renderer.render_to_pdf(document_ir, output_pdf_path)
        logger.success(f"✓ PDF已生成: {output_pdf_path}")
        return True
    except Exception as e:
        logger.error(f"✗ PDF生成失败: {e}")
        logger.exception("详细错误信息:")
        return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ir_json_path = sys.argv[1]
    output_pdf_path = sys.argv[2] if len(sys.argv) > 2 else None

    # 检查环境变量
    import os
    if 'DYLD_LIBRARY_PATH' not in os.environ:
        logger.warning("未设置DYLD_LIBRARY_PATH，尝试自动设置...")
        os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

    success = export_to_pdf(ir_json_path, output_pdf_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
