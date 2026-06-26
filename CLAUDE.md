/# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Video subtitle burning tool — overlays timestamped text from `.txt` subtitle files onto videos using FFmpeg's `drawtext` filter. Interactive CLI that scans `videos/` for `.mp4` + `.txt` pairs, lets the user pick a font and size preset, then batch encodes with burned-in subtitles to `output/`.

## Commands

```bash
python main.py          # Run the tool (interactive)
```

No test suite, linters, or build step exists. The only runtime dependency beyond Python stdlib is **FFmpeg** (must be compiled with `libfreetype` — verified at startup via `ffmpeg -version`).

## Architecture

```
main.py                  # Entry point: orchestrates the interactive workflow
config.py                # Constants only — font size presets, color, directories, file extensions
subtitle_parser.py       # Parses (start, end) text subtitle format, one entry per line
burner.py                # FFmpeg drawtext filter construction + subprocess execution
utils.py                 # File scanning, interactive prompts, FFmpeg binary discovery, resolution probing
```

### Data flow

1. `main.py` checks FFmpeg availability → scans `fonts/` for `.ttf`/`.otf` → user selects font
2. User selects font size preset (1–4, maps to % of video height)
3. `utils.scan_videos()` pairs videos in `videos/` with same-basename `.txt` files
4. Per video: `subtitle_parser.parse_subtitle_file()` → list of `{start, end, text}` dicts
5. `burner.build_drawtext_filters()` 为每条字幕创建临时文件写入原文（零转义），构建 `drawtext=textfile='...':enable='between(t,start,end)'` 链式 filter
6. `burner.burn_subtitles()` runs FFmpeg with `-vf` (or `-filter_script:v` for very long filter chains >30k chars) — re-encodes video to H.264 (`libx264`, medium preset, CRF 23), copies audio stream

### Key design decisions

- **Font size is resolution-aware**: computed as `video_height * ratio` where ratio is the chosen preset (3.5%–7.0%). This auto-adapts to 9:16 portrait and 16:9 landscape.
- **FFmpeg binary discovery**: checks Scoop shims directories first (`~/scoop/shims`, `%USERPROFILE%\scoop\shims`, `C:\scoop\shims`), falls back to bare command name from PATH.
- **Subtitle Y position**: anchored to `video_height * (1 - SUBTITLE_BOTTOM_RATIO) - text_h`, placing the text block's bottom edge at a fixed distance from the frame bottom.
- **Long filter chain fallback**: when the `drawtext` chain exceeds 30,000 characters (close to Windows' 32,767 command-line limit), the filter string is written to a temp file and passed via `-filter_script:v` instead of `-vf`.
- **字幕文本传递：必须用 `textfile=`，禁止用 `text=` 内联**。FFmpeg drawtext filter 的内部解析器**不支持**在单引号字符串内转义单引号——`'\''`（shell 风格）和 `\'`（反斜杠转义）都无效，`\'` 在链式 filter 中会导致 `enable='between(t,0,1)'` 里的逗号被误解析为 filter 分隔符（报 `No such filter: '0'`）。唯一绕过的 hex escape `\x27` 虽然可行但不优雅。最终方案：`burner.build_drawtext_filters()` 将每条字幕写入独立临时文件，通过 `textfile='...'` 引用，文本内容零转义直接读取。`utils.escape_drawtext()` 已废弃，仅保留供参考。**永远不要再走 `text=` 内联 + 转义的路线。**
- **已废弃 — drawtext escaping** (`escape_drawtext`): order matters — backslashes first, then `%`, then `:`, then single quotes (using `'\''` hand-rolling to stay inside single-quoted text).

### Subtitle file format

```
(0.0, 2.06) 字幕文本内容
(2.64, 5.74) 下一句字幕
```

Regex: `\((\d+\.?\d*),\s*(\d+\.?\d*)\)\s*(.+)`. Seconds can be integer or float. Empty lines are skipped. `start >= end` raises `ValueError`.

### Directories

| Directory | Purpose |
|-----------|---------|
| `fonts/`  | User places `.ttf`/`.otf` files here (gitignored except `.gitkeep`) |
| `videos/` | Input `.mp4`/`.mov`/`.mkv`/`.avi`/`.webm` + matching `.txt` subtitles (gitignored except `.gitkeep`) |
| `output/` | Burned `.mp4` files written here as `<basename>_subtitled.mp4` (gitignored except `.gitkeep`) |
