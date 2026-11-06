# Scattered Scripts

该仓库收集了一些用于不同目的的零散的 Python 和 JavaScript 脚本。为防止忘记在这里记录它们的用法。

某些脚本在 [Wana_Blog](https://watanabechika.github.io/Wana_blog) 中出现且有详细说明，下面会具体标注。

## 目录

- [activitywatch_yearbook.py](#activitywatch_yearbookpy)
- [ass_name_to_video.py](#ass_name_to_videopy)
- [bgm_cancel_process.js](#bgm_cancel_processjs)
- [bgm_tag_stats.js](#bgm_tag_statsjs)
- [common_ygo_cards.py](#common_ygo_cardspy)
- [fetch_bgm_data.py](#fetch_bgm_datapy)
- [ffmpeg_multi_process.py](#ffmpeg_multi_processpy)
- [fourier_beats.py](#fourier_beatspy)
- [killer_sudoku.py](#killer_sudokupy)
- [mp3_to_ogg.py](#mp3_to_oggpy)
- [music_replace_for_ff15.py](#music_replace_for_ff15py)
- [rmvb_avi_to_mp4.py](#rmvb_avi_to_mp4py)
- [shuiyuan_pin_to_unread.js](#shuiyuan_pin_to_unreadjs)
- [spider_for_llwiki_bpm.py](#spider_for_llwiki_bpmpy)
- [video_object_panorama.py](#video_object_panorama.py)

## `activitywatch_yearbook.py`

- **动机**:
    activitywatch 是一个日常挂在电脑后台监控的软件，包括窗口、鼠标键盘点击、浏览器页面等。都监控一年了，这不得拿来总结总结。其实就是统计瘾犯了。

- **介绍**:
    这是一个读取本机后台 `activitywatch` 软件并生成结构化年度统计报告数据的脚本。通过直接对 `activitywatch` 监控端口发请求获取数据，因此省去了下载庞大的原始数据文件。

- **功能**:
    - 读取各类监控的桶数据。
    - 分析这些数据，生成用于作图的结构化统计结果。

- **用法**:
    1. 在相同目录下放置个人分类配置 `aw-category-export-default.json`，然后再文件开头调整其余配置：端口号、数据年份等。
    2. `python activitywatch_yearbook.py`

## `ass_name_to_video.py`

- **动机**:
    很多时候，从另外网站下载的字幕和对应的视频名称完全不同，可能只有**指示集数的数字**相同。mpv 自动读取字幕脚本只能识别主文件名相同，只有后缀不同的字幕文件到对应的视频文件，因此有必要将文件名对应统一起来。

- **介绍**:
    修改目录下的所有字幕文件名称，使其和对应的视频名称相同。主要是通过指示集数的数字来对应的。

- **功能**:
    - 自动分析指示集数的数字来对应字幕文件和视频文件。支持两集合并的字幕（如 01~02），并按顺序一一对应视频。最后以视频文件名为准。
    - 自动对指示语言的字幕文件名后缀进行处理（如 tc/sc），不影响数量匹配和结果。
    - 支持 .ass/.ssa 文件。

- **用法**:
    - 将要处理的全部字幕文件放到和对应视频同一目录下。
    - `python ass_name_to_video.py <文件夹> [-n]`，`-n` 表示试运行，不实际修改。

## `bgm_cancel_process.js`

- **动机**:
    重刷动画的时候，格子是之前就点满了的，不能点格子记录进度。同时也和[点击看过时自动完成所有进度](https://bgm.tv/dev/app/461)互为镜像。

- **介绍**:
    点击在看时自动撤销所有进度。

- **功能**:
    在章节页面内修改收藏状态为在看，且所有单集（不含sp）都被标记为看过时，会自动撤销所有进度。对动画和三次元有效。

- **用法**:
    请在[ Bangumi 超合金组件处](https://bgm.tv/dev/app/5163)订阅该插件。

## `bgm_tag_stats.js`

- **动机**:
    统计瘾犯了，加之 Bangumi 上还真没有对**标签**进行统计的插件。

- **介绍**:
    对用户收藏条目的标签进行统计。

- **功能**:
    - 对用户收藏条目中可用于筛选搜索的标签进行统计和可视化，默认只针对当前年份。入口在用户页简介下方。
    - 使用 charts.js 进行可视化。

- **用法**:
    请在[ Bangumi 超合金组件处](https://bgm.tv/dev/app/5129)订阅该插件。

## `common_ygo_cards.py`

- **动机**:
    在做 [Wana_tools](https://github.com/WatanabeChika/Wana_tools) 的游戏王卡图猜猜乐时，为了降低难度，想到只获取常用卡片。而 MyCard 的 MCPro 决斗数据库中正好有卡片使用率统计。于是写脚本以获取数据。

- **介绍**:
    该脚本会调用 MyCard 的接口，遍历多个时间维度与数据来源，将返回数据中所有分类的卡片 `id` 收集、去重并保存为 `common_cards.json`。**最大用途是给 Github Action 提供自动更新脚本。**

- **功能**:
    - 遍历时间区间与来源组合，自动批量请求并进度提示。
    - 从返回 JSON 的各分类中提取 `id`，使用集合去重。
    - 结果排序后输出到本地 `common_cards.json`。
    - 每次请求间隔 2 秒，降低被限流风险。

- **用法**:
    - 在脚本所在目录执行：
      ```powershell
      python .\common_ygo_cards.py
      ```
    - 运行完成后在当前目录生成 `common_cards.json`，内容为去重后的卡片 ID 列表。

## `fetch_bgm_data.py`

- **动机**:
    统计瘾犯了，动画相关数据也要总结出报告才行。

- **介绍**:
    对某一年用户看过的动画相关数据进行统计分析，包括时长、声优、制作公司、标签等。

- **功能**:
    - 通过 Bangumi API 获取各类数据。如果遇到没有标注时长的集数，根据该条目的类型（TV / 剧场版 / Web / OVA 等）进行估算。
    - 分析这些数据，生成用于作图的结构化统计结果。

- **用法**:
    1. 在文件开头调整个人配置：ID、agent&token、**条目排除列表**等。
    2. `python fetch_bgm_data.py`


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
详见：[给歌曲加点特效](https://watanabechika.github.io/Wana_blog/posts/coding/maybe_useful/audio_effect.md)

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
    2.  在 `if __name__ == "__main__":` 部分，取消注释想要应用的效果函数。
    3.  运行脚本：`python fourier_beats.py`。

## `killer_sudoku.py`
详见：[Kill the Killer-Sudoku problem](https://watanabechika.github.io/Wana_blog/posts/coding/maybe_useful/killer_sudoku.html)

- **动机**:
    每天在 [Daily Killer Sudoku](https://www.dailykillersudoku.com/) 上做一道数独，于是自然想到能否让计算机做。之前有利用回溯法写过解决普通数独的算法 ~~（早忘了）~~，这次试试杀手数独。

- **介绍**:
    一个杀手数独（Killer Sudoku）求解器。

- **功能**:
    - 使用回溯算法来寻找谜题的解。
    - 包含一个可选的命令行可视化功能，可以实时展示求解过程（但这会显著降低求解速度）。
    - 谜题通过“笼子”（cages）来定义，即一组总和固定的单元格。

- **用法**:
    1.  在脚本中定义杀手数独谜题的 `cages` 结构。脚本内已包含几个示例。
    2.  在 `solver = KillerSudokuSolver(cages_5)` 这一行选择要使用的谜题。
    3.  通过设置 `solver.solve(visualization=False)` 中的 `visualization` 参数来启用或禁用可视化。
    4.  运行脚本：`python killer_sudoku.py`。

## `mp3_to_ogg.py`

- **动机**:
    游戏《欧洲卡车模拟 2》（Euro Truck Simulator 2）只能解析 OGG 格式的音频格式文件，需要批量转换格式的脚本。

- **介绍**:
    一个在 MP3 和 OGG 音频格式之间进行批量转换的工具。

- **功能**:
    - 支持从 MP3 到 OGG 和从 OGG 到 MP3 的双向转换。
    - 使用多线程并行处理，转换速度快。

- **用法**:
    1.  运行脚本：`python mp3_to_ogg.py`。
    2.  根据提示，依次输入源文件夹路径、目标文件夹路径以及转换方向（`1` 代表 MP3 -> OGG，`2` 代表 OGG -> MP3）。

## `music_replace_for_ff15.py`
详见：[雷迦利亚牌随身听，启动](https://watanabechika.github.io/Wana_blog/posts/acg/game/ff15_radio.html)

- **动机**:
    想在《最终幻想 15》（Final Fantasy XV）里开车听自己的音乐，但是该游戏自定义音乐文件较麻烦，于是写脚本。

- **介绍**:
    这是一个非常特殊的脚本，用于替换游戏《最终幻想 15》中的车载音乐。

- **功能**:
    - 依赖一个名为 `FFXVRT.exe` 的外部工具。
    - 脚本内硬编码了游戏音乐文件与本地音乐文件的映射关系。

- **用法**:
    1.  确保 `FFXVRT.exe` 在脚本的运行目录下。
    2.  根据需求，修改脚本中的文件路径和音乐映射。
    3.  运行脚本：`python music_replace.py`。

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
        - 指定输出目录：`python rmvb_avi_to_mp4.py <输入目录> -o <输出目录>`
        - 覆盖已存在文件：`python rmvb_avi_to_mp4.py <输入目录> -f`
        - 转换后删除原文件：`python rmvb_avi_to_mp4.py <输入目录> -r`

## `shuiyuan_pin_to_unread.js`

- **动机**:
    由于种种原因，水源社区里有些话题不会显示在“未读”页面（不知道是否是 discourse 的 bug），自己手动找又很麻烦，因此需要一个“置顶”功能。

- **介绍**:
    将想跟进的帖子固定在水源未读页面（/unread）顶部。

- **功能**:
    - 在话题页面可直接点击标题旁的置顶来固定话题。
    - 在未读页面，被置顶的话题会固定显示在最上方。

- **用法**:
    将该脚本添加至油猴（tampermonkey，浏览器扩展）中，启用即可。

## `spider_for_llwiki_bpm.py`
详见：[通过 BPM 挑选合适的歌曲](https://watanabechika.github.io/Wana_blog/posts/coding/maybe_useful/bpm_check.html)

- **动机**:
    统计瘾犯了，且想找到符合步调的适合步行/跑步时听的歌。

- **介绍**:
    一个网络爬虫，用于从 `llwiki.org` 网站上抓取《Love Live!》系列所有歌曲的 BPM（每分钟节拍数）信息。

- **功能**:
    - `get_all_bpm`: 爬取所有歌曲的 BPM 并保存到 `data.json`。
    - `data_process`: 对抓取的数据进行分类（如无 BPM、BPM 可变、适合步行的 BPM、适合跑步的 BPM），并保存到 `result.json`。
    - `draw_bpm`: 将分类后的数据可视化，生成 BPM 分布的条形图并保存为 `bpm1.png` 和 `bpm2.png`。

- **用法**:
    1.  在 `if __name__ == '__main__':` 部分，按需调用 `get_all_bpm()`、`data_process()` 或 `draw_bpm()` 函数。
    2.  运行脚本：`python spider_for_llwiki_bpm.py`。

## `video_object_panorama.py`
详见：[移动竹管，能窥见整只猎豹吗？](https://watanabechika.github.io/Wana_blog/posts/coding/maybe_useful/panorama_in_video.html)
- **动机**:
    在给动画整理截图的时候想到的：有的场景一张截图截不完，能够通过视频处理得到一张连续的全景图就好了。

- **介绍**:
    一个通过解析视频片段，拼接全景图的脚本。mpv 插件版点[这里](https://github.com/WatanabeChika/mpv-video-paronama-generator)。

- **功能**:
    - 依次进行抽帧、特征提取以及全景拼接。
    - 优先使用 SIFT 算法智能识别视频片段中的图像特征，计算每张关键帧图片的单应性矩阵后通过正确的方式融合拼接在一起。
    - 在特征提取和图像扭曲阶段采用多线程处理加速，在图像叠加混合阶段采用向量化处理和 ROI 局部运算加速。

- **用法**:
    运行脚本 `python video_object_panorama.py <input_video> <output_image> --start <start_time> --end <end_time> [--sample-fps <fps>]`