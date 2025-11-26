# Scattered Scripts

该仓库收集了一些用于不同目的的零散的 Python 脚本。为防止忘记在这里记录它们的用法。

某些脚本在 [Wana_Blog](https://watanabechika.github.io/Wana_blog) 中出现且有详细说明，下面会具体标注。

## `ffmpeg_multi_process.py`

- **动机**:
    在电脑上用 mpv 配合外挂/内封字幕看动画，但是移动设备不支持外挂/内封字幕，于是需要用 ffmpeg 重编码。当需要处理的数量变多，就需要批量重编码的脚本了。

- **介绍**:
    这是一个使用 `ffmpeg` 进行视频批量处理的工具，主要功能是将字幕硬编码（烧录）到视频中。它利用 `hevc_nvenc` 进行硬件加速编码，以提高处理效率。

- **功能**:
    - 支持两种字幕模式：
        1.  **外部字幕**: 字幕是独立的 `.ass` 文件。
        2.  **内封字幕**: 字幕流封装在视频容器（如 `.mkv`）内部。
    - 脚本顶部的常量（如 `INPUT_FILE_FORMAT`, `SUBTITLE_LANGUAGE` 等）可以根据需要进行配置。

- **用法**:
    - **处理外部字幕**:
        ```bash
        python ffmpeg_multi_process.py <输入文件夹路径> <输出文件夹路径>
        ```
    - **处理内封字幕**:
        ```bash
        python ffmpeg_multi_process.py <输入文件夹路径> <输出文件夹路径> --inside_sub
        ```

## `fourier_beats.py`
详见：[给歌曲加点特效](https://watanabechika.github.io/Wana_blog/posts/coding/audio_effect.html)

- **动机**:
    看到一些“将歌曲的第二拍和第四拍互换”的视频，觉得很有意思，于是应运而生。

- **介绍**:
    该脚本使用傅里叶变换和节拍分析，为音频文件应用多种有趣的音效。

- **功能**:
    - `apply_phone_filter`: 模拟电话音效（带通滤波）。
    - `apply_dizzy_effect`: 添加回声或“眩晕”效果。
    - `apply_cut_frequencies`: 移除特定间隔的频率，产生一种特殊音效。
    - `swap_beats`: 交换每四拍中的第二拍和第四拍，创造出新的节奏感。

- **用法**:
    1.  在脚本中修改 `input_path` 和 `output_path` 变量，以指定输入和输出文件。
    2.  在 `if __name__ == "__main__":` 部分，取消注释你想要应用的效果函数。
    3.  运行脚本: `python fourier_beats.py`。

## `killer_sudoku.py`
详见：[Kill the Killer-Sudoku problem](https://watanabechika.github.io/Wana_blog/posts/coding/killer_sudoku.html)

- **动机**:
    每天在 [Daily Killer Sudoku](https://www.dailykillersudoku.com/) 上做一道数独，于是自然想到能否让计算机做。之前有利用回溯法写过解决普通数独的算法 ~~（早忘了）~~，这次试试杀手数独。

- **介绍**:
    一个杀手数独（Killer Sudoku）求解器。

- **功能**:
    - 使用回溯算法来寻找谜题的解。
    - 包含一个可选的命令行可视化功能，可以实时展示求解过程（但这会显著降低求解速度）。
    - 谜题通过“笼子”（cages）来定义，即一组总和固定的单元格。

- **用法**:
    1.  在脚本中定义你的杀手数独谜题的 `cages` 结构。脚本内已包含几个示例。
    2.  在 `solver = KillerSudokuSolver(cages_5)` 这一行选择你要使用的谜题。
    3.  通过设置 `solver.solve(visualization=False)` 中的 `visualization` 参数来启用或禁用可视化。
    4.  运行脚本: `python killer_sudoku.py`。

## `mp3_to_ogg.py`

- **动机**:
    游戏《欧洲卡车模拟2》（Euro Truck Simulator 2）只能解析 OGG 格式的音频格式文件，需要批量转换格式的脚本。

- **介绍**:
    一个在 MP3 和 OGG 音频格式之间进行批量转换的工具。

- **功能**:
    - 支持从 MP3 到 OGG 和从 OGG 到 MP3 的双向转换。
    - 使用多线程并行处理，转换速度快。

- **用法**:
    1.  运行脚本: `python mp3_to_ogg.py`。
    2.  根据提示，依次输入源文件夹路径、目标文件夹路径以及转换方向（`1` 代表 MP3 -> OGG，`2` 代表 OGG -> MP3）。

## `music_replace_for_ff15.py`
详见：[雷迦利亚牌随身听，启动](https://watanabechika.github.io/Wana_blog/posts/acg/ff15_radio.html)

- **动机**:
    想在《最终幻想15》（Final Fantasy XV）里开车听自己的音乐，但是该游戏自定义音乐文件较麻烦，于是写脚本。

- **介绍**:
    这是一个非常特殊的脚本，用于替换游戏《最终幻想15》中的车载音乐。

- **功能**:
    - 依赖一个名为 `FFXVRT.exe` 的外部工具。
    - 脚本内硬编码了游戏音乐文件与本地音乐文件的映射关系。

- **用法**:
    1.  确保 `FFXVRT.exe` 在脚本的运行目录下。
    2.  根据你的需求，修改脚本中的文件路径和音乐映射。
    3.  运行脚本: `python music_replace.py`。

## `rmvb_avi_to_mp4.py`

- **动机**:
    大批量下载电影时，由于源不同，想统一最后的格式。挨个用 ffmpeg 很麻烦，于是写脚本。

- **介绍**:
    将指定目录及其子目录下的所有 `.rmvb` 和 `.avi` 视频文件批量转换为 `.mp4` 格式。

- **功能**:
    - 使用 `ffmpeg` 和 `hevc_nvenc` 进行硬件加速转换。
    - 支持递归扫描文件夹。
    - 可以选择是否覆盖已存在的输出文件。
    - 可以选择在转换成功后删除原始文件。

- **用法**:
    - **基本用法**:
        ```bash
        python rmvb_avi_to_mp4.py <要扫描的目录路径>
        ```
    - **高级选项**:
        - 指定输出目录: `python rmvb_avi_to_mp4.py <输入目录> -o <输出目录>`
        - 覆盖已存在文件: `python rmvb_avi_to_mp4.py <输入目录> -f`
        - 转换后删除原文件: `python rmvb_avi_to_mp4.py <输入目录> -r`

## `spider_for_llwiki_bpm.py`

- **作用**:
    一个网络爬虫，用于从 `llwiki.org` 网站上抓取《Love Live!》系列所有歌曲的BPM（每分钟节拍数）信息。

- **功能**:
    - `get_all_bpm`: 爬取所有歌曲的 BPM 并保存到 `data.json`。
    - `data_process`: 对抓取的数据进行分类（如无 BPM、BPM 可变、适合步行的 BPM、适合跑步的 BPM），并保存到 `result.json`。
    - `draw_bpm`: 将分类后的数据可视化，生成 BPM 分布的条形图并保存为 `bpm1.png` 和 `bpm2.png`。

- **用法**:
    1.  在 `if __name__ == '__main__':` 部分，按需调用 `get_all_bpm()`、`data_process()` 或 `draw_bpm()` 函数。
    2.  运行脚本: `python spider_for_llwiki_bpm.py`。
