#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把文件夹里的 .ass / .ssa 字幕文件重命名成对应集数的视频文件名。

特性：
  * 自动识别集数——支持两集合并的字幕（如 [01-02]），按顺序一一对应视频。
    例如视频有 10 集，字幕为 01-02, 03-04, ..., 17-18, 19 → 依次对应 1..10。
  * 同一集有多个字幕文件时，自动识别语言标记（sc/tc/jp/en…），
    以 .sc.ass / .tc.ssa 的形式拼到视频名后面。
  * 扩展名沿用源文件（.ssa 还是 .ssa，.ass 还是 .ass）。

用法：
    python ass_name_to_video.py <文件夹> [-n]
    -n / --dry-run   只预览，不实际重命名
"""

import re
import argparse
from pathlib import Path
from collections import defaultdict

VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.rmvb', '.flv', '.wmv', '.ts', '.m2ts', '.webm'}
SUB_EXTS = {'.ass', '.ssa'}

# 语言标记：越具体的放前面
LANG_PATTERNS = [
    (r'sc|chs|gb|simp|zh[-_]?cn|简体|简中|简',     'sc'),
    (r'tc|cht|big5|trad|zh[-_]?tw|繁体|繁中|繁',   'tc'),
    (r'jp|jpn|jap|日语|日文',                      'jp'),
    (r'en|eng|english|英语|英文',                  'en'),
]
LANG_REGEXES = [
    (re.compile(r'(?i)(?<![A-Za-z0-9])(' + p + r')(?![A-Za-z0-9])'), tag)
    for p, tag in LANG_PATTERNS
]


def detect_lang(stem):
    """从文件名主干中识别语言标记，返回 'sc'/'tc'/'jp'/'en' 或 None。"""
    for regex, tag in LANG_REGEXES:
        if regex.search(stem):
            return tag
    return None


def tokens_of(path):
    """返回文件名主干中所有数字，形如 [(数值, 起点, 终点), ...]。"""
    return [(int(m.group()), m.start(), m.end())
            for m in re.finditer(r'\d+', path.stem)]


def guess_video_episodes(files):
    """
    识别视频集数：按「数字出现的位置」找那个值构成连续整数区间的位置。
    例如视频命名为 …-01、…-02、…、…-13 时，位置上的值 1..13 连续，命中。
    """
    tokens = {f: tokens_of(f) for f in files}

    by_pos = {}
    for toks in tokens.values():
        for i, (val, _, _) in enumerate(toks):
            by_pos.setdefault(i, []).append(val)

    best_pos, best_count = None, 0
    for i, vals in by_pos.items():
        distinct = set(vals)
        if len(distinct) < 2:
            continue
        if max(distinct) - min(distinct) + 1 == len(distinct):
            if len(distinct) > best_count:
                best_count, best_pos = len(distinct), i

    return {
        f: (toks[best_pos][0] if best_pos is not None and best_pos < len(toks) else None)
        for f, toks in tokens.items()
    }


def find_key_position(subs):
    """
    在所有字幕文件中找出最靠左的「变化数字」位置——这个位置上的数字
    就是用来排序的键。组名(11)、分辨率(960/720)、CRC 哈希等要么不变，
    要么出现在更靠右的位置，自然会被跳过。
    """
    by_pos = defaultdict(list)
    for s in subs:
        for i, (val, _, _) in enumerate(tokens_of(s)):
            by_pos[i].append(val)

    varying = [i for i, vals in by_pos.items()
               if len(vals) == len(subs) and len(set(vals)) > 1]
    return min(varying) if varying else None


def main():
    parser = argparse.ArgumentParser(
        description='把 .ass/.ssa 字幕文件名改成对应集数视频文件的名字')
    parser.add_argument('folder', nargs='?', default='.',
                        help='文件夹路径，默认为当前目录')
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help='只显示结果，不实际重命名')
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f'错误：{folder} 不是文件夹')
        return 1

    videos = sorted(p for p in folder.iterdir()
                    if p.is_file() and p.suffix.lower() in VIDEO_EXTS)
    subs = sorted(p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() in SUB_EXTS)

    if not videos:
        print('没有找到视频文件')
        return 1
    if not subs:
        print('没有找到字幕文件')
        return 1

    print(f'视频 {len(videos)} 个，字幕 {len(subs)} 个\n')

    # 1) 识别视频集数并按集数排序
    vid_eps = guess_video_episodes(videos)
    video_list = []
    for v in videos:
        ep = vid_eps[v]
        if ep is None:
            print(f'[警告] 无法识别视频集数：{v.name}')
            continue
        video_list.append((ep, v))
    video_list.sort(key=lambda x: x[0])

    # 2) 找字幕的排序键位置
    key_pos = find_key_position(subs)
    if key_pos is None:
        print('无法确定字幕排序键位置，退出')
        return 1

    # 3) 按排序键把字幕分组（同一范围的不同语言进同一组）
    groups = defaultdict(list)
    for s in subs:
        toks = tokens_of(s)
        if key_pos < len(toks):
            groups[toks[key_pos][0]].append(s)
        else:
            print(f'[跳过] 无法提取排序键：{s.name}')

    sorted_keys = sorted(groups.keys())

    if len(sorted_keys) != len(video_list):
        print(f'[提示] 字幕组数 {len(sorted_keys)} 与视频数 '
              f'{len(video_list)} 不一致，按较小值配对')

    # 4) 按顺序一一配对，生成重命名计划
    plan = []  # [(src_path, new_name_str)]
    n_pairs = min(len(sorted_keys), len(video_list))
    for i in range(n_pairs):
        key = sorted_keys[i]
        ep, video = video_list[i]
        base = video.stem
        group = groups[key]

        if len(group) == 1:
            s = group[0]
            plan.append((s, f'{base}{s.suffix}'))
        else:
            used = set()
            for s in group:
                lang = detect_lang(s.stem)
                if lang is None or lang in used:
                    j = 1
                    while f'part{j}' in used:
                        j += 1
                    lang = f'part{j}'
                    print(f'[提示] {s.name} 未能识别语言标记，使用 .{lang}')
                used.add(lang)
                plan.append((s, f'{base}.{lang}{s.suffix}'))

    # 5) 执行
    print()
    renamed = skipped = 0
    for src, new_name in plan:
        if new_name == src.name:
            print(f'[跳过] 名称已一致：{src.name}')
            continue
        dst = src.with_name(new_name)
        if dst.exists() and dst != src:
            print(f'[冲突] 目标已存在，跳过：{new_name}')
            skipped += 1
            continue
        print(f'{src.name}  ->  {new_name}')
        if not args.dry_run:
            src.rename(dst)
        renamed += 1

    print()
    tail = '（dry-run 模式，未实际修改）' if args.dry_run else ''
    print(f'完成：{renamed} 个已重命名，{skipped} 个被跳过{tail}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())