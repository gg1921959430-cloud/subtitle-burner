# 视频字幕烧录工具

将 `.txt` 字幕文件烧录到视频上。

## 字幕格式

每行一条字幕，格式：

```
(开始秒, 结束秒) 字幕文本
```

示例：

```
(0.0, 2.06) 雪花落在外派赌场，
(2.64, 5.74) 霓虹向你眼睛闪烁，
```

## 准备工作

1. **安装 FFmpeg**（需包含 libfreetype）：

   ```bash
   # Windows (scoop)
   scoop install ffmpeg

   # macOS
   brew install ffmpeg

   # Linux
   sudo apt install ffmpeg
   ```

2. **放置字体文件**：将 `.ttf` 或 `.otf` 字体文件放入 `fonts/` 目录。

3. **放置视频和字幕**：将视频文件（`.mp4`）和同名的字幕文件（`.txt`）放入 `videos/` 目录。

   ```
   videos/
   ├── demo1.mp4
   ├── demo1.txt
   ├── demo2.mp4
   └── demo2.txt
   ```

## 使用

```bash
python main.py
```

按提示选择字体和字号大小，工具会自动扫描 `videos/` 下的视频文件并匹配同名字幕，批量烧录后输出到 `output/` 目录。

## 目录结构

```
subtitle_burner/
├── fonts/                  # 放置 .ttf 字体文件
├── videos/                 # 放置 .mp4 和同名 .txt
├── output/                 # 输出烧录完成的视频
├── main.py                 # 主入口
├── config.py               # 配置
├── subtitle_parser.py      # 字幕解析
├── burner.py               # FFmpeg 烧录核心
├── utils.py                # 工具函数
├── requirements.txt        # 依赖
└── README.md               # 本文件
```

## 字号说明

| 档位 | 名称 | 占视频高度比例 |
|------|------|---------------|
| 1 | 小小 | 3.5% |
| 2 | 小 | 4.5% |
| 3 | 中 | 5.5% |
| 4 | 大 | 7.0% |

字号根据视频实际高度动态计算，自动适配 9:16 竖屏和 16:9 横屏。
