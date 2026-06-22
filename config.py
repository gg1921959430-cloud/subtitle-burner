"""配置项 — 字体大小档位映射（基于视频高度的百分比）。"""

# 字体大小四档：小小 / 小 / 中 / 大
# 值表示字体像素大小占视频高度的比例
FONT_SIZE_PRESETS = {
    1: {"name": "小小", "ratio": 0.035},   # 视频高度的 3.5%
    2: {"name": "小",   "ratio": 0.045},   # 视频高度的 4.5%
    3: {"name": "中",   "ratio": 0.055},   # 视频高度的 5.5%
    4: {"name": "大",   "ratio": 0.070},   # 视频高度的 7.0%
}

# 字幕位置：距底部的比例（相对于视频高度）
SUBTITLE_BOTTOM_RATIO = 0.08  # 距底部 8%

# 字幕颜色与背景
FONT_COLOR = "white"                # 字体颜色
SHADOW_COLOR = "black@0.6"          # 阴影颜色及透明度
SHADOW_OFFSET = 2                   # 阴影偏移像素

# 输入输出目录
VIDEO_DIR = "videos"
OUTPUT_DIR = "output"
FONTS_DIR = "fonts"

# 支持的文件扩展名
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
SUBTITLE_EXT = ".txt"
FONT_EXTS = {".ttf", ".otf"}
