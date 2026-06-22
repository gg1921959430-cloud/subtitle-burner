"""工具函数 — 文件扫描、交互选择、视频信息获取。"""

import json
import os
import subprocess
import sys
from typing import List, Dict, Optional, Tuple

from config import (
    VIDEO_DIR,
    OUTPUT_DIR,
    FONTS_DIR,
    VIDEO_EXTS,
    SUBTITLE_EXT,
    FONT_EXTS,
    FONT_SIZE_PRESETS,
)


def _find_scoop_shims() -> str:
    """查找 Scoop 安装的 shims 目录。"""
    possible = [
        os.path.expanduser("~/scoop/shims"),
        os.path.expandvars("%USERPROFILE%\\scoop\\shims"),
        "C:\\scoop\\shims",
    ]
    for p in possible:
        if os.path.isdir(p):
            return p
    return ""


def _find_ffmpeg_bin(name: str) -> str:
    """
    查找 FFmpeg 工具二进制文件路径。

    优先使用 PATH 中的命令；如果找不到，搜索 scoop shims 目录。

    Args:
        name: 工具名，如 "ffmpeg", "ffprobe"

    Returns:
        可执行文件的完整路径，或仅返回名称（若 PATH 中可直接调用）
    """
    # 先尝试 scoop shims 里的完整路径
    shims = _find_scoop_shims()
    if shims:
        full = os.path.join(shims, f"{name}.exe")
        if os.path.isfile(full):
            return full
    # 回退到 PATH 中的命令
    return name


def ensure_dirs() -> None:
    """确保必要目录存在。"""
    for d in [VIDEO_DIR, OUTPUT_DIR, FONTS_DIR]:
        os.makedirs(d, exist_ok=True)


def scan_fonts() -> List[str]:
    """
    扫描 fonts/ 目录下的字体文件。

    Returns:
        字体文件名列表（不含路径）
    """
    fonts = []
    if not os.path.isdir(FONTS_DIR):
        return fonts
    for f in os.listdir(FONTS_DIR):
        ext = os.path.splitext(f)[1].lower()
        if ext in FONT_EXTS:
            fonts.append(f)
    fonts.sort()
    return fonts


def scan_videos() -> List[Dict]:
    """
    扫描 videos/ 目录，匹配视频和字幕。

    Returns:
        [
            {
                "video": "demo1.mp4",
                "subtitle": "demo1.txt",  # 或 None
                "video_path": "videos/demo1.mp4",
                "subtitle_path": "videos/demo1.txt",  # 或 None
            },
            ...
        ]
    """
    pairs = []
    if not os.path.isdir(VIDEO_DIR):
        return pairs

    # 收集视频文件
    video_files = []
    for f in os.listdir(VIDEO_DIR):
        ext = os.path.splitext(f)[1].lower()
        if ext in VIDEO_EXTS:
            video_files.append(f)
    video_files.sort()

    for vf in video_files:
        base = os.path.splitext(vf)[0]
        sub_file = base + SUBTITLE_EXT
        sub_path = os.path.join(VIDEO_DIR, sub_file)
        if os.path.isfile(sub_path):
            pairs.append({
                "video": vf,
                "subtitle": sub_file,
                "video_path": os.path.join(VIDEO_DIR, vf),
                "subtitle_path": sub_path,
            })
        else:
            pairs.append({
                "video": vf,
                "subtitle": None,
                "video_path": os.path.join(VIDEO_DIR, vf),
                "subtitle_path": None,
            })
    return pairs


def choose_font(fonts: List[str]) -> str:
    """
    交互式选择字体。

    Args:
        fonts: 可用字体文件名列表

    Returns:
        选中的字体文件名
    """
    print("请选择字体：")
    for i, f in enumerate(fonts, 1):
        print(f"  [{i}] {f}")
    while True:
        try:
            choice = int(input("请输入数字: ").strip())
            if 1 <= choice <= len(fonts):
                return fonts[choice - 1]
            print(f"请输入 1~{len(fonts)} 之间的数字")
        except ValueError:
            print("请输入有效数字")


def choose_font_size() -> int:
    """
    交互式选择字体大小档位。

    Returns:
        档位编号 (1-4)
    """
    print("\n请选择字体大小：")
    for k, v in FONT_SIZE_PRESETS.items():
        print(f"  [{k}] {v['name']}")
    while True:
        try:
            choice = int(input("请输入数字: ").strip())
            if choice in FONT_SIZE_PRESETS:
                return choice
            print(f"请输入 1~{len(FONT_SIZE_PRESETS)} 之间的数字")
        except ValueError:
            print("请输入有效数字")


def get_video_resolution(video_path: str) -> Tuple[int, int]:
    """
    用 ffprobe 获取视频分辨率（宽, 高）。

    Args:
        video_path: 视频文件路径

    Returns:
        (width, height)
    """
    ffprobe = _find_ffmpeg_bin("ffprobe")
    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        stream = info["streams"][0]
        return stream["width"], stream["height"]
    except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as e:
        print(f"  ✘ 无法获取视频分辨率: {e}", file=sys.stderr)
        return 1920, 1080  # 默认 1080p


def check_ffmpeg() -> bool:
    """检查系统是否安装了 FFmpeg（含 libfreetype）。"""
    ffmpeg = _find_ffmpeg_bin("ffmpeg")
    try:
        result = subprocess.run(
            [ffmpeg, "-version"], capture_output=True, text=True, check=True
        )
        output = result.stdout
        if "freetype" not in output.lower():
            print(
                "⚠ 警告: FFmpeg 可能未编译 libfreetype 支持，"
                "drawtext filter 将无法使用。",
                file=sys.stderr,
            )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✘ 错误: 未找到 FFmpeg，请先安装 FFmpeg 并加入 PATH。", file=sys.stderr)
        return False


def escape_drawtext(text: str) -> str:
    """
    转义 drawtext filter 中的特殊字符。

    FFmpeg drawtext 中需要转义的字符：冒号:、反斜杠\、单引号'（在单引号包裹时）
    这里将文本包裹在单引号中，内部单引号做转义处理。

    参考: ffmpeg drawtext text='...'
    转义规则（单引号内）：
        - 单引号 ' 替换为 '\''（结束单引号 → 转义单引号 → 重新开始单引号）
        - 百分号 % 替换为 \\% （避免被解析为文本扩展）
        - 冒号 : 替换为 \\: （避免被解析为参数分隔符）
    """
    # 先转义反斜杠（必须最先）
    text = text.replace("\\", "\\\\")
    # 转义百分号
    text = text.replace("%", "\\%")
    # 转义冒号
    text = text.replace(":", "\\:")
    # 转义单引号：结束当前引号，转义单引号，重新开始
    text = text.replace("'", "'\\''")
    return text
