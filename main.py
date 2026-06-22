"""主入口 — 视频字幕烧录工具。"""

import os
import sys
import time
from typing import List

from config import (
    FONT_SIZE_PRESETS,
    OUTPUT_DIR,
    FONTS_DIR,
)
from utils import (
    ensure_dirs,
    scan_fonts,
    scan_videos,
    choose_font,
    choose_font_size,
    check_ffmpeg,
)
from subtitle_parser import parse_subtitle_file
from burner import burn_subtitles


def main() -> None:
    """主流程：交互式选择 → 批量处理。"""
    print("\n======= 视频字幕烧录工具 =======\n")

    # 0. 环境检查
    if not check_ffmpeg():
        sys.exit(1)

    ensure_dirs()

    # 1. 扫描字体
    fonts = scan_fonts()
    if not fonts:
        print(f"✘ 错误: 字体目录 '{FONTS_DIR}/' 下未找到 .ttf 或 .otf 文件。")
        print(f"请将字体文件放入 '{FONTS_DIR}/' 目录后重试。")
        sys.exit(1)
    selected_font = choose_font(fonts)
    font_path = os.path.abspath(os.path.join(FONTS_DIR, selected_font))

    # 2. 选择字号
    size_choice = choose_font_size()
    size_info = FONT_SIZE_PRESETS[size_choice]

    # 3. 扫描视频
    print()
    pairs = scan_videos()
    if not pairs:
        print(f"✘ 错误: 视频目录 '{OUTPUT_DIR}' 下未找到视频文件。")
        print(f"支持格式: .mp4, .mov, .mkv, .avi, .webm")
        sys.exit(1)

    print(f"扫描到 {len(pairs)} 个视频：")
    for p in pairs:
        status = "✔ 已匹配字幕" if p["subtitle"] else "✘ 无匹配字幕"
        print(f"  - {p['video']} {status}")
    print()

    # 4. 批量处理
    success_count = 0
    total = len(pairs)
    for i, pair in enumerate(pairs, 1):
        video_name = pair["video"]
        print(f"[{i}/{total}] 正在处理: {video_name} ...")

        # 检查字幕匹配
        if not pair["subtitle"]:
            print(f"    ✘ 跳过: 未找到匹配的字幕文件 ({os.path.splitext(video_name)[0]}.txt)")
            continue

        # 解析字幕
        try:
            entries = parse_subtitle_file(pair["subtitle_path"])
        except (ValueError, FileNotFoundError) as e:
            print(f"    ✘ 字幕解析失败: {e}")
            continue

        if not entries:
            print(f"    ✘ 跳过: 字幕文件为空")
            continue

        print(f"    字幕条数: {len(entries)}")

        # 计算字体大小：基于视频高度 × 比例
        from utils import get_video_resolution
        _, video_height = get_video_resolution(pair["video_path"])
        font_size = int(video_height * size_info["ratio"])

        # 烧录
        output_filename = os.path.splitext(video_name)[0] + "_subtitled.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        success = burn_subtitles(
            video_path=pair["video_path"],
            subtitle_path=pair["subtitle_path"],
            output_path=output_path,
            entries=entries,
            font_size=font_size,
            font_path=font_path,
        )

        if success:
            success_count += 1
            print(f"    ✔ 输出: {output_path}")
        else:
            print(f"    ✘ 处理失败")

    # 5. 完成
    print(f"\n全部完成！成功 {success_count}/{total} 个")


if __name__ == "__main__":
    main()
