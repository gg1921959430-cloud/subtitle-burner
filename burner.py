"""烧录核心 — 用 FFmpeg drawtext filter 将字幕烧录到视频上。

使用 textfile= 参数替代 text= 内联文本，每条字幕写入独立临时文件，
从根本上消除 FFmpeg filter 解析器的转义问题。
"""

import os
import subprocess
import sys
import tempfile
from typing import List, Dict, Tuple

from config import (
    FONT_COLOR,
    SHADOW_COLOR,
    SHADOW_OFFSET,
    SUBTITLE_BOTTOM_RATIO,
    OUTPUT_DIR,
    FONTS_DIR,
)
from utils import get_video_resolution, _find_ffmpeg_bin


def _escape_filter_path(path: str) -> str:
    """
    转义 FFmpeg filter 字符串中的文件路径。

    FFmpeg filter 解析器中，路径内的反斜杠和冒号需要转义。
    注意：这只用于路径，不用于用户生成的文本内容。

    Args:
        path: 文件系统路径

    Returns:
        FFmpeg filter 安全的路径字符串
    """
    return path.replace("\\", "\\\\").replace(":", "\\:")


def build_drawtext_filters(
    entries: List[Dict],
    video_width: int,
    video_height: int,
    font_size: int,
    font_path: str,
) -> Tuple[str, List[str]]:
    """
    构建 FFmpeg drawtext filter chain 字符串。

    每条字幕写入独立临时文件，通过 textfile= 参数引用，
    文本内容原样写入文件，完全绕过 FFmpeg filter 解析器的转义问题。

    Args:
        entries: 字幕条目列表
        video_width: 视频宽度
        video_height: 视频高度
        font_size: 字体像素大小
        font_path: 字体文件的绝对路径

    Returns:
        (filter_chain, temp_files)
        - filter_chain: FFmpeg -vf 参数值，格式 "drawtext=...,drawtext=..."
        - temp_files:   临时文本文件路径列表，调用方负责在使用后清理
    """
    font_path_escaped = _escape_filter_path(font_path)

    # 字幕 Y 坐标：距底部 SUBTITLE_BOTTOM_RATIO 比例
    y_position = int(video_height * (1 - SUBTITLE_BOTTOM_RATIO))

    filter_parts = []
    temp_files = []

    for entry in entries:
        start = entry["start"]
        end = entry["end"]
        text = entry["text"]

        # 每条字幕写入独立临时文件，原文不需要任何转义
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        )
        tmp.write(text)
        tmp.close()
        temp_files.append(tmp.name)

        # enable 表达式：在 start~end 之间启用
        enable_expr = f"between(t,{start},{end})"

        # 构建单条 drawtext（使用 textfile 替代 text）
        drawtext = (
            f"drawtext="
            f"fontfile='{font_path_escaped}':"
            f"textfile='{_escape_filter_path(tmp.name)}':"
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

    return ",".join(filter_parts), temp_files


def _cleanup_temp_files(temp_files: List[str]) -> None:
    """清理字幕临时文本文件。"""
    for f in temp_files:
        try:
            os.unlink(f)
        except OSError:
            pass


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

    # 构建 drawtext filter chain（同时生成字幕临时文件）
    filter_chain, temp_files = build_drawtext_filters(
        entries, video_width, video_height, font_size, font_path
    )

    try:
        # 检查 filter chain 长度，超长则使用 filter_script 文件
        if len(filter_chain) > 30000:
            print(f"    filter chain 较长 ({len(filter_chain)} 字符)，使用 filter_script 文件...")
            return _burn_with_script(video_path, output_path, filter_chain)

        ffmpeg = _find_ffmpeg_bin("ffmpeg")
        cmd = [
            ffmpeg,
            "-i", video_path,
            "-vf", filter_chain,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            "-y",
            output_path,
        ]

        return _run_ffmpeg(cmd)
    finally:
        _cleanup_temp_files(temp_files)


def _burn_with_script(
    video_path: str,
    output_path: str,
    filter_chain: str,
) -> bool:
    """使用 filter_script 文件执行烧录（绕过命令行长度限制）。"""
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
        )
        if result.returncode == 0:
            return True
        print(f"    ✘ FFmpeg 错误 (返回码 {result.returncode}):", file=sys.stderr)
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
