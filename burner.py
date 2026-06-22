"""烧录核心 — 用 FFmpeg drawtext filter 将字幕烧录到视频上。"""

import os
import subprocess
import sys
import tempfile
from typing import List, Dict

from config import (
    FONT_COLOR,
    SHADOW_COLOR,
    SHADOW_OFFSET,
    SUBTITLE_BOTTOM_RATIO,
    OUTPUT_DIR,
    FONTS_DIR,
)
from utils import escape_drawtext, get_video_resolution, _find_ffmpeg_bin


def build_drawtext_filters(
    entries: List[Dict],
    video_width: int,
    video_height: int,
    font_size: int,
    font_path: str,
) -> str:
    """
    构建 FFmpeg drawtext filter chain 字符串。

    每个字幕条目生成一个 enable + drawtext filter，串联成一个逗号分隔的链。

    Args:
        entries: 字幕条目列表
        video_width: 视频宽度
        video_height: 视频高度
        font_size: 字体像素大小
        font_path: 字体文件的绝对路径

    Returns:
        FFmpeg -vf 参数值，格式: "drawtext=...,drawtext=..."
    """
    # 字体路径转义（Windows 路径中的反斜杠和冒号）
    font_path_escaped = font_path.replace("\\", "\\\\").replace(":", "\\:")

    # 字幕 Y 坐标：距底部 SUBTITLE_BOTTOM_RATIO 比例
    y_position = int(video_height * (1 - SUBTITLE_BOTTOM_RATIO))

    filter_parts = []
    for entry in entries:
        start = entry["start"]
        end = entry["end"]
        text = escape_drawtext(entry["text"])

        # enable 表达式：在 start~end 之间启用
        enable_expr = f"between(t,{start},{end})"

        # 构建单条 drawtext
        drawtext = (
            f"drawtext="
            f"fontfile='{font_path_escaped}':"
            f"text='{text}':"
            f"fontsize={font_size}:"
            f"fontcolor={FONT_COLOR}:"
            f"shadowcolor={SHADOW_COLOR}:"
            f"shadowx={SHADOW_OFFSET}:"
            f"shadowy={SHADOW_OFFSET}:"
            f"x=(w-text_w)/2:"          # 水平居中
            f"y={y_position}-text_h:"    # 底部安全区域（文本框底部对齐 y）
            f"enable='{enable_expr}'"
        )
        filter_parts.append(drawtext)

    return ",".join(filter_parts)


def burn_subtitles(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    entries: List[Dict],
    font_size: int,
    font_path: str,
) -> bool:
    """
    烧录字幕到视频。

    Args:
        video_path: 输入视频路径
        subtitle_path: 字幕文件路径（未使用，保留接口）
        output_path: 输出视频路径
        entries: 字幕条目列表
        font_size: 字体像素大小
        font_path: 字体文件路径

    Returns:
        是否成功
    """
    video_width, video_height = get_video_resolution(video_path)
    print(f"    分辨率: {video_width}x{video_height}, 字体大小: {font_size}px")

    # 构建 drawtext filter chain
    filter_chain = build_drawtext_filters(
        entries, video_width, video_height, font_size, font_path
    )

    # 检查 filter chain 长度，超长则使用 filter_script 文件
    # FFmpeg 命令行长度限制通常在 32767 字符（Windows）
    if len(filter_chain) > 30000:
        print(f"    filter chain 较长 ({len(filter_chain)} 字符)，使用 filter_script 文件...")
        return _burn_with_script(
            video_path, output_path, filter_chain
        )

    # 用 FFmpeg 执行烧录
    # 使用 -vf 传入 filter chain，视频流 copy 编码为 H.264（兼容性好）
    ffmpeg = _find_ffmpeg_bin("ffmpeg")
    cmd = [
        ffmpeg,
        "-i", video_path,
        "-vf", filter_chain,
        "-c:v", "libx264",      # 重新编码为 H.264
        "-preset", "medium",    # 编码速度/质量平衡
        "-crf", "23",           # 质量控制
        "-c:a", "copy",         # 音频直接复制
        "-y",                   # 覆盖输出
        output_path,
    ]

    return _run_ffmpeg(cmd)


def _burn_with_script(
    video_path: str,
    output_path: str,
    filter_chain: str,
) -> bool:
    """使用 filter_script 文件执行烧录（绕过命令行长度限制）。"""
    # 写入临时 filter_script 文件
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.txt', delete=False, encoding='utf-8'
    ) as f:
        f.write(filter_chain)
        script_path = f.name

    try:
        ffmpeg = _find_ffmpeg_bin("ffmpeg")
        cmd = [
            ffmpeg,
            "-i", video_path,
            "-filter_script:v", script_path,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            "-y",
            output_path,
        ]
        return _run_ffmpeg(cmd)
    finally:
        os.unlink(script_path)


def _run_ffmpeg(cmd: list) -> bool:
    """执行 FFmpeg 命令并显示进度。"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            # 不直接 check=True，手动处理以便输出错误信息
        )
        if result.returncode == 0:
            return True
        print(f"    ✘ FFmpeg 错误 (返回码 {result.returncode}):", file=sys.stderr)
        # 只打印最后几行错误信息
        stderr_lines = result.stderr.strip().split('\n')
        for line in stderr_lines[-5:]:
            if line.strip():
                print(f"      {line.strip()}", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        print(f"    ✘ FFmpeg 执行失败: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("    ✘ 未找到 FFmpeg 命令", file=sys.stderr)
        return False
