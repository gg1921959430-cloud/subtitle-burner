"""字幕解析器 — 解析 (开始秒, 结束秒) 字幕文本 格式的字幕文件。"""

import re
from typing import List, Dict

# 匹配格式: (数字, 数字) 任意文本
PATTERN = re.compile(r'\((\d+\.?\d*),\s*(\d+\.?\d*)\)\s*(.+)')


def parse_subtitle_file(filepath: str) -> List[Dict]:
    """
    解析字幕文件，返回结构化字幕列表。

    Args:
        filepath: 字幕 .txt 文件路径

    Returns:
        [
            {"start": 0.0,  "end": 2.06, "text": "雪花落在外派赌场，"},
            {"start": 2.64, "end": 5.74, "text": "霓虹向你眼睛闪烁，"},
        ]

    Raises:
        ValueError: 当某行格式不匹配时
        FileNotFoundError: 文件不存在时
    """
    entries = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            match = PATTERN.match(line)
            if not match:
                raise ValueError(
                    f"第 {line_no} 行格式不正确: {line}\n"
                    f"期望格式: (开始秒, 结束秒) 字幕文本"
                )
            start = float(match.group(1))
            end = float(match.group(2))
            text = match.group(3).strip()
            if start >= end:
                raise ValueError(
                    f"第 {line_no} 行: 开始时间({start}) 必须小于结束时间({end})"
                )
            entries.append({"start": start, "end": end, "text": text})
    return entries
