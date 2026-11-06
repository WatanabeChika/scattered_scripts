import json
import math
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta
import requests

# ================= 1. 基础配置 =================
AW_API_BASE = "http://127.0.0.1:5600/api/0"
TARGET_YEAR = 2026
# 类别导出文件固定从脚本所在目录读取，避免从其他工作目录启动时意外退回内置规则。
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORY_FILE = os.path.join(SCRIPT_DIR, "aw-category-export-default.json")
OUTPUT_JSON_PATH = f"aw-annual-{TARGET_YEAR}.json"

COUNTS_PER_METER = 31500.0
SCROLL_METERS_PER_TICK = 0.0264
KEY_FORCE_KG = 0.05
MAX_SINGLE_EVENT_SEC = 4 * 3600

BUILTIN_CATEGORIES = [
    {"id": 0, "name": ["Work"], "depth": 0, "color": "#4ade80", "regex": r"Google Docs|libreoffice|ReText|PowerPoint|POWERPNT|SJTU|Word|WINWORD|Excel|EXCEL|腾讯会议|实验室组会", "ignore_case": True},
    {"id": 1, "name": ["Work", "Programming"], "depth": 1, "color": "#38bdf8", "regex": r"GitHub|Stack Overflow|BitBucket|Gitlab|vim|Spyder|kate|Ghidra|Scite|Windows|API|Gemini|Visual Studio Code|Code\.exe|Chill With You|Android Studio|Codex|VMware", "ignore_case": False},
    {"id": 2, "name": ["Work", "Programming", "ActivityWatch"], "depth": 2, "color": "#0284c7", "regex": r"ActivityWatch|aw-", "ignore_case": True},
    {"id": 18, "name": ["Work", "Programming", "Earworm Diary"], "depth": 2, "color": "#818cf8", "regex": r"Daily Music Record|V2157A|Earworm Diary|耳虫日记", "ignore_case": False},
    {"id": 3, "name": ["Work", "Image"], "depth": 1, "color": "#34d399", "regex": r"GIMP|Inkscape|Photoshop", "ignore_case": False},
    {"id": 4, "name": ["Work", "Video"], "depth": 1, "color": "#2dd4bf", "regex": r"Kdenlive|Premiere|Aegisub", "ignore_case": False},
    {"id": 5, "name": ["Work", "Audio"], "depth": 1, "color": "#a3e635", "regex": r"Audacity", "ignore_case": False},
    {"id": 6, "name": ["Work", "3D"], "depth": 1, "color": "#fbbf24", "regex": r"Blender", "ignore_case": False},
    {"id": 7, "name": ["Media"], "depth": 0, "color": "#f87171", "regex": None, "ignore_case": False},
    {"id": 8, "name": ["Media", "Games"], "depth": 1, "color": "#fb923c", "regex": r"Minecraft|RimWorld|masterduel|Steam|雀魂麻將|Euro Truck Simulator|Muse Dash|MuseDash|Danganronpa|MDPro3|PORTAL|Sid Meier's Civilization|prospi|Celeste|文字遊戲|CookingSimulator|双影奇境|みんなのリズム天国|SKETCHY MASSAGE|OriAndTheWilloftheWisps|Iron Nest: Heavy Turret Simulator|Four Nights at the Burger Shop|Human|Planet of Lana|Portal|Out of the Park Baseball 27|House Flipper Game", "ignore_case": False},
    {"id": 9, "name": ["Media", "Video"], "depth": 1, "color": "#f43f5e", "regex": r"YouTube|Plex|VLC|bilibili|哔哩哔哩|画中画", "ignore_case": True},
    {"id": 16, "name": ["Media", "Anime"], "depth": 1, "color": "#f472b6", "regex": r"Bangumi|mpv|Syncplay|漫画柜下载器", "ignore_case": True},
    {"id": 10, "name": ["Media", "Social Media"], "depth": 1, "color": "#facc15", "regex": r"reddit|Facebook|Twitter|Instagram|devRant|水源社区|朋友圈|Weixin|WeChat", "ignore_case": True},
    {"id": 11, "name": ["Media", "Music"], "depth": 1, "color": "#a8fc00", "regex": r"Spotify|Deezer|MusicPlayer2|网易云音乐|cloudmusic", "ignore_case": True},
    {"id": 12, "name": ["Comms"], "depth": 0, "color": "#a78bfa", "regex": r"Mozilla Firefox|firefox|Hiddify|Edge|msedge|WizTree|Clash|360压缩|Program Manager", "ignore_case": True},
    {"id": 13, "name": ["Comms", "IM"], "depth": 1, "color": "#22d3ee", "regex": r"Messenger|Telegram|Signal|WhatsApp|Rambox|Slack|Riot|Element|Discord|Nheko|NeoChat|Mattermost|QQ", "ignore_case": False},
    {"id": 14, "name": ["Comms", "Email"], "depth": 1, "color": "#38bdf8", "regex": r"Gmail|Thunderbird|mutt|alpine", "ignore_case": False},
    {"id": 17, "name": ["Comms", "Files"], "depth": 1, "color": "#94a3b8", "regex": r"文件资源管理器|explorer\.exe|百度网盘|Free Download Manager|图片查看器|iTunes|Dism\+\+x64|夸克网盘", "ignore_case": True},
    {"id": 15, "name": ["Uncategorized"], "depth": 0, "color": "#9ca3af", "regex": None, "ignore_case": False},
]

# 动态宏类别的兜底配色。实际类别颜色优先读取 ActivityWatch 导出文件中的 data.color。
MACRO_COLOR_PALETTE = [
    "#38bdf8", "#34d399", "#fb923c", "#f472b6", "#facc15",
    "#a78bfa", "#2dd4bf", "#818cf8", "#94a3b8", "#a3e635",
]
# 最终图表分类数量上限（包含母分类、独立子分类及“未分类”）。
MAX_MACRO_GROUPS = 8
# 子分类至少占所属母分类总时长的该比例，才有资格独立展示。
# 例如 0.05 表示至少占母分类（母类自身 + 全部子类）5%。
MIN_CHILD_CATEGORY_SHARE = 0.05


PRETTY_NAME_MAP = {
    "Sid Meier's Civilization": "文明VI",
    "文明": "文明VI",
    "Out of the Park Baseball 27": "OOTP 棒球",
    "Euro Truck Simulator": "欧卡2",
    "OriAndTheWilloftheWisps": "奥日2",
    "Iron Nest: Heavy Turret Simulator": "Iron Nest",
    "Four Nights at the Burger Shop": "Burger Shop",
    "House Flipper Game": "房产达人",
    "みんなのリズム天国": "节奏天国",
    "MuseDash": "Muse Dash",
    "Muse Dash": "Muse Dash",
    "PORTAL": "Portal",
    "Visual Studio Code": "VS Code",
    "Code.exe": "VS Code",
    "Mozilla Firefox": "Firefox",
    "firefox.exe": "Firefox",
    "POWERPNT.EXE": "PowerPoint",
    "POWERPNT": "PowerPoint",
    "WINWORD.EXE": "Word",
    "EXCEL.EXE": "Excel",
    "Weixin.exe": "微信",
    "Weixin": "微信",
    "WeChat.exe": "微信",
    "explorer.exe": "资源管理器",
    "文件资源管理器": "资源管理器",
    "bilibili": "哔哩哔哩",
    "Daily Music Record": "耳虫日记",
    "Earworm Diary": "耳虫日记",
    "V2157A": "耳虫日记",
    "cloudmusic.exe": "网易云音乐",
    "cloudmusic": "网易云音乐",
    "MusicPlayer2.exe": "MusicPlayer2",
    "musicplayer2": "MusicPlayer2",
}

EXCLUDED_ENTITIES = {
    "Uncategorized", "Unknown", "Program Manager", "Game", "game",
    "ApplicationFrameHost", "SystemSettings", "SearchHost", "LockApp",
    "ShellExperienceHost", "TextInputHost", "dwm", "conhost", "未知"
}


def prettify_name(raw_name: str) -> str:
    if not raw_name:
        return "未知"
    cleaned = raw_name.strip()
    if cleaned in PRETTY_NAME_MAP:
        return PRETTY_NAME_MAP[cleaned]
    for k, v in PRETTY_NAME_MAP.items():
        if k.lower() == cleaned.lower():
            return v
    cleaned = re.sub(r"\.exe$", "", cleaned, flags=re.IGNORECASE)
    return cleaned[:16]


def strip_domain_from_title(raw_title: str) -> str:
    if not raw_title:
        return ""
    text = re.sub(r"\s*-\s*Mozilla Firefox$", "", str(raw_title).strip(), flags=re.IGNORECASE)
    parts = [p.strip() for p in text.split("|") if p.strip()]
    if len(parts) > 1:
        clean_parts = [
            p for p in parts
            if not re.search(r"([a-z0-9-]+\.)+[a-z]{2,}", p, re.IGNORECASE)
            and not p.lower().startswith(("http://", "https://"))
        ]
        if clean_parts:
            return " - ".join(clean_parts)[:36]
        return parts[-1][:36]
    return re.sub(r"https?://\S+", "", text).strip()[:36]


def _is_uncategorized_category(category: dict) -> bool:
    """通过类别路径识别未分类项，不依赖固定 category id。"""
    path = category.get("name") or []
    if isinstance(path, str):
        path = [path]
    if not path:
        return False
    leaf = str(path[-1]).strip().lower().replace("_", " ").replace("-", " ")
    return leaf in {
        "uncategorized", "uncategorised", "unclassified", "not classified",
        "unknown", "未分类", "未分类项", "未分类应用",
    }


def build_macro_groups(categories: list):
    """构建候选分类树：每个顶层类别作为母分类，第一层子类作为候选子分类。

    是否保留子分类不在这里决定，而是在读取全年事件、得到真实使用时长后决定。
    这样可以按实际时长挑选重要子类，其余自动合并到母分类。
    """
    group_defs = {}
    category_to_key = {}
    fallback_key = ("__uncategorized__",)
    root_keys = {}

    def ensure_root(root_name: str, category=None):
        key = ("root", root_name)
        definition = group_defs.setdefault(key, {
            "label": root_name,
            "color": None,
            "is_uncategorized": False,
            "is_parent": True,
            "parent_key": None,
            "sort_path": (root_name, ""),
        })
        if category:
            data = category.get("data") or {}
            definition["label"] = (
                category.get("macro_label") or data.get("macro_label")
                or (category.get("name") or [root_name])[0]
            )
            definition["color"] = (
                category.get("macro_color") or data.get("macro_color")
                or category.get("color") or definition.get("color")
            )
        root_keys[root_name] = key
        return key

    for category in categories:
        category_id = category.get("id")
        path = category.get("name") or []
        if isinstance(path, str):
            path = [path]
        path = [str(part) for part in path]
        depth = int(category.get("depth", max(0, len(path) - 1)))
        data = category.get("data") or {}

        if _is_uncategorized_category(category):
            category_to_key[category_id] = fallback_key
            group_defs.setdefault(fallback_key, {
                "label": category.get("macro_label") or data.get("macro_label") or path[-1],
                "color": category.get("macro_color") or data.get("macro_color") or category.get("color"),
                "is_uncategorized": True,
                "is_parent": False,
                "parent_key": None,
                "sort_path": ("~uncategorized",),
            })
            continue

        if not path:
            continue

        root_name = path[0]
        root_key = ensure_root(root_name)

        if depth == 0:
            # 根类别的匹配事件直接归入母分类；无规则根节点仍作为子分类折叠的接收组。
            ensure_root(root_name, category)
            category_to_key[category_id] = root_key
            continue

        child_name = path[1] if len(path) > 1 else root_name
        explicit_group = category.get("macro_group") or data.get("macro_group")
        if explicit_group:
            # 自定义组仍归属于其路径对应的母分类；如同一自定义组跨母类，分别处理以免映射歧义。
            child_key = ("custom", root_name, str(explicit_group))
            default_label = (
                category.get("macro_label") or data.get("macro_label") or str(explicit_group)
            )
        else:
            child_key = ("child", root_name, child_name)
            default_label = category.get("macro_label") or data.get("macro_label") or child_name

        child_def = group_defs.setdefault(child_key, {
            "label": str(default_label),
            "color": category.get("macro_color") or data.get("macro_color") or category.get("color"),
            "is_uncategorized": False,
            "is_parent": False,
            "parent_key": root_key,
            "sort_path": (root_name, child_name),
        })
        if not child_def.get("color"):
            child_def["color"] = (
                category.get("macro_color") or data.get("macro_color") or category.get("color")
            )
        category_to_key[category_id] = child_key

    # 即使导出文件没有 Uncategorized 节点，也为未匹配事件保留兜底组。
    group_defs.setdefault(fallback_key, {
        "label": "Uncategorized",
        "color": None,
        "is_uncategorized": True,
        "is_parent": False,
        "parent_key": None,
        "sort_path": ("~uncategorized",),
    })

    # 固定顺序：母分类 -> 候选子分类 -> 未分类。
    parent_keys = sorted(
        (key for key, value in group_defs.items() if value.get("is_parent")),
        key=lambda key: tuple(str(part).casefold() for part in group_defs[key]["sort_path"]),
    )
    child_keys = sorted(
        (key for key, value in group_defs.items()
         if not value.get("is_parent") and not value.get("is_uncategorized")),
        key=lambda key: tuple(str(part).casefold() for part in group_defs[key]["sort_path"]),
    )
    ordered_keys = parent_keys + child_keys + [fallback_key]

    # 候选阶段不急于给重名子类添加母类前缀。最终是否保留某个子类，
    # 要等全年时长筛选后才能确定；只对最终同时出现的重名分类消歧。
    macro_groups = {}
    key_to_macro = {}
    for macro_id, key in enumerate(ordered_keys, start=1):
        definition = group_defs[key]
        label = definition["label"]
        color = definition.get("color") or MACRO_COLOR_PALETTE[(macro_id - 1) % len(MACRO_COLOR_PALETTE)]
        macro_groups[macro_id] = {
            "label": label,
            "color": color,
            "is_uncategorized": bool(definition["is_uncategorized"]),
            "is_parent": bool(definition.get("is_parent")),
            "parent_id": None,
            "sort_path": definition["sort_path"],
        }
        key_to_macro[key] = macro_id

    for macro_id, key in enumerate(ordered_keys, start=1):
        parent_key = group_defs[key].get("parent_key")
        if parent_key in key_to_macro:
            macro_groups[macro_id]["parent_id"] = key_to_macro[parent_key]

    category_to_macro = {
        category_id: key_to_macro[group_key]
        for category_id, group_key in category_to_key.items()
    }
    fallback_macro_id = key_to_macro[fallback_key]
    return macro_groups, category_to_macro, fallback_macro_id


def collapse_macro_groups(
    candidate_groups: dict,
    usage_seconds: dict,
    max_groups: int = MAX_MACRO_GROUPS,
    min_child_share: float = MIN_CHILD_CATEGORY_SHARE,
):
    """按子类占所属母类的时长比例筛选，并将最终分类数严格限制在 max_groups。

    子类比例的分母 = 母类直接使用时长 + 该母类下所有候选子类使用时长。
    被独立保留的子类会映射到自己的最终 ID，不再计入母类；未保留子类
    则映射到母类，因此母类统计只包含母类自身及被折叠的子类。
    """
    if max_groups < 2:
        raise ValueError("max_groups 至少为 2，才能同时容纳分类和未分类")
    if not 0 <= min_child_share <= 1:
        raise ValueError("min_child_share 必须位于 [0, 1]")

    parent_ids = [
        macro_id for macro_id, meta in candidate_groups.items()
        if meta.get("is_parent")
    ]
    child_ids = [
        macro_id for macro_id, meta in candidate_groups.items()
        if not meta.get("is_parent") and not meta.get("is_uncategorized")
    ]
    fallback_ids = [
        macro_id for macro_id, meta in candidate_groups.items()
        if meta.get("is_uncategorized")
    ]
    fallback_old_id = fallback_ids[0] if fallback_ids else None
    reserved_fallback = 1 if fallback_old_id is not None else 0

    # 统计母类总时长，仅用于判断子类占比；最终输出时不会把被独立展示的子类
    # 再加回母类。
    parent_total_usage = {
        pid: max(0.0, float(usage_seconds.get(pid, 0.0))) for pid in parent_ids
    }
    for cid in child_ids:
        parent_id = candidate_groups[cid].get("parent_id")
        if parent_id in parent_total_usage:
            parent_total_usage[parent_id] += max(
                0.0, float(usage_seconds.get(cid, 0.0))
            )

    # 超出预算时保留时长最高的母类，其余母类及其子类统一汇入“其他类别”。
    parent_budget = max_groups - reserved_fallback
    other_parent_old_ids = set()
    synthetic_other = False
    if len(parent_ids) > parent_budget:
        keep_parent_count = max(0, parent_budget - 1)
        keep_parent_ids = set(sorted(
            parent_ids,
            key=lambda pid: parent_total_usage.get(pid, 0.0),
            reverse=True,
        )[:keep_parent_count])
        other_parent_old_ids = set(parent_ids) - keep_parent_ids
        parent_ids = [pid for pid in parent_ids if pid in keep_parent_ids]
        synthetic_other = True

    # 只允许占所属母类总时长达到阈值的子类参与名额竞争；再按绝对使用时长排序。
    child_budget = max(
        0, max_groups - len(parent_ids) - reserved_fallback - int(synthetic_other)
    )
    child_shares = {}
    eligible_children = []
    for cid in child_ids:
        parent_id = candidate_groups[cid].get("parent_id")
        child_usage = max(0.0, float(usage_seconds.get(cid, 0.0)))
        parent_total = parent_total_usage.get(parent_id, 0.0)
        share = child_usage / parent_total if parent_total > 0 else 0.0
        child_shares[cid] = share
        if (
            parent_id in parent_ids
            and child_usage > 0
            and share >= min_child_share
        ):
            eligible_children.append(cid)

    keep_child_ids = set(sorted(
        eligible_children,
        key=lambda cid: (
            -max(0.0, float(usage_seconds.get(cid, 0.0))),
            str(candidate_groups[cid].get("label", "")).casefold(),
        ),
    )[:child_budget])

    # 最终组顺序：母分类、独立子分类、“其他类别”（如需要）、未分类。
    ordered_old_ids = list(parent_ids) + sorted(
        keep_child_ids,
        key=lambda cid: (
            -max(0.0, float(usage_seconds.get(cid, 0.0))),
            str(candidate_groups[cid].get("label", "")).casefold(),
        ),
    )
    if fallback_old_id is not None:
        ordered_old_ids.append(fallback_old_id)

    final_groups = {}
    old_to_new = {}
    for new_id, old_id in enumerate(ordered_old_ids, start=1):
        meta = candidate_groups[old_id]
        final_groups[new_id] = {
            "label": meta["label"],
            "color": meta["color"],
            "is_uncategorized": bool(meta.get("is_uncategorized")),
            "is_parent": bool(meta.get("is_parent")),
            "parent_id": None,
        }
        old_to_new[old_id] = new_id

    other_new_id = None
    if synthetic_other:
        other_new_id = len(final_groups) + 1
        final_groups[other_new_id] = {
            "label": "其他类别",
            "color": MACRO_COLOR_PALETTE[(other_new_id - 1) % len(MACRO_COLOR_PALETTE)],
            "is_uncategorized": False,
            "is_parent": True,
            "parent_id": None,
        }
        for old_id in other_parent_old_ids:
            old_to_new[old_id] = other_new_id

    # 被淘汰的子类归入自己的母类；母类被折叠时则归入“其他类别”。
    for cid in child_ids:
        if cid in keep_child_ids:
            continue
        parent_id = candidate_groups[cid].get("parent_id")
        if parent_id in old_to_new:
            old_to_new[cid] = old_to_new[parent_id]
        elif other_new_id is not None:
            old_to_new[cid] = other_new_id
        elif fallback_old_id is not None:
            old_to_new[cid] = old_to_new[fallback_old_id]

    # 为独立展示的子类写入最终母类 ID，便于前端按层级展示（不参与时长累计）。
    for cid in keep_child_ids:
        final_child_id = old_to_new[cid]
        parent_id = candidate_groups[cid].get("parent_id")
        final_parent_id = old_to_new.get(parent_id)
        final_groups[final_child_id]["parent_id"] = final_parent_id

    # 只根据“最终保留下来的类别”判断名称是否冲突。
    # 例如 Work > Video 被合并、Media > Video 被保留时，最终标签就是 Video；
    # 只有两个 Video 都独立展示时，才分别显示 Work / Video、Media / Video。
    label_to_ids = defaultdict(list)
    for macro_id, meta in final_groups.items():
        label_to_ids[str(meta.get("label", "")).casefold()].append(macro_id)

    for duplicate_ids in label_to_ids.values():
        if len(duplicate_ids) < 2:
            continue
        for macro_id in duplicate_ids:
            meta = final_groups[macro_id]
            parent_id = meta.get("parent_id")
            if parent_id in final_groups:
                parent_label = final_groups[parent_id]["label"]
                meta["label"] = f"{parent_label} / {meta['label']}"

    # 极少数情况下（例如同名根分类）前缀后仍冲突，使用完整路径作为最后兜底。
    resolved_labels = defaultdict(list)
    for macro_id, meta in final_groups.items():
        resolved_labels[str(meta.get("label", "")).casefold()].append(macro_id)
    for duplicate_ids in resolved_labels.values():
        if len(duplicate_ids) < 2:
            continue
        for macro_id in duplicate_ids:
            meta = final_groups[macro_id]
            original = str(meta["label"])
            path = candidate_groups.get(next(
                (old_id for old_id, new_id in old_to_new.items() if new_id == macro_id), None
            ), {}).get("sort_path")
            if path:
                meta["label"] = " / ".join(str(part) for part in path if part)
            elif meta.get("is_uncategorized"):
                meta["label"] = "未分类"
            else:
                meta["label"] = f"{original} ({macro_id})"

    fallback_new_id = (
        old_to_new.get(fallback_old_id) if fallback_old_id is not None else None
    )
    if fallback_new_id is None:
        fallback_new_id = next(
            (mid for mid, meta in final_groups.items() if meta.get("is_uncategorized")),
            max(final_groups, default=1),
        )

    if len(final_groups) > max_groups:
        raise RuntimeError(
            f"最终分类数 {len(final_groups)} 超过上限 {max_groups}"
        )
    return final_groups, old_to_new, fallback_new_id, keep_child_ids


def load_category_rules():
    categories = BUILTIN_CATEGORIES
    if os.path.exists(CATEGORY_FILE):
        with open(CATEGORY_FILE, "r", encoding="utf-8") as f:
            export_data = json.load(f)
        raw_categories = (
            export_data.get("categories", []) if isinstance(export_data, dict)
            else export_data
        )
        if raw_categories:
            categories = []
            for item in raw_categories:
                rule = item.get("rule") or {}
                data = item.get("data") or {}
                path = item.get("name") or []
                if isinstance(path, str):
                    path = [path]
                categories.append({
                    "id": item.get("id"),
                    "name": path,
                    "depth": item.get("depth", len(path) - 1),
                    "color": data.get("color") or item.get("color"),
                    "regex": rule.get("regex") if rule.get("type") == "regex" else None,
                    "ignore_case": bool(rule.get("ignore_case", item.get("ignore_case", False))),
                    "macro_group": item.get("macro_group") or data.get("macro_group"),
                    "macro_label": item.get("macro_label") or data.get("macro_label"),
                    "macro_color": item.get("macro_color") or data.get("macro_color"),
                })
        print(f"[分类] 已从 {CATEGORY_FILE} 读取 {len(categories)} 个类别")
    else:
        print(f"[分类] 未找到 {CATEGORY_FILE}，使用脚本内置类别规则")

    compiled_rules = []
    for category in sorted(categories, key=lambda item: item.get("depth", 0), reverse=True):
        if not category.get("regex"):
            continue
        flags = re.IGNORECASE if category.get("ignore_case", False) else 0
        try:
            compiled_rules.append((category, re.compile(category["regex"], flags)))
        except re.error as exc:
            print(f"[分类][警告] 类别 {category.get('name')} 的正则无效，已跳过：{exc}")

    meta_map = {category.get("id"): category for category in categories}
    candidate_groups, category_to_macro, fallback_macro_id = build_macro_groups(categories)
    print(
        f"[分类] 已建立 {len(candidate_groups)} 个候选分类（含母分类和子分类）；"
        f"最终将按全年使用时长筛选，最多保留 {MAX_MACRO_GROUPS} 个"
    )
    return compiled_rules, meta_map, candidate_groups, category_to_macro, fallback_macro_id


def match_category(text: str, compiled_rules, fallback_category_id):
    for category, pattern in compiled_rules:
        match = pattern.search(text)
        if match:
            return category["id"], prettify_name(match.group(0))
    return fallback_category_id, "Uncategorized"


def parse_event_interval(ev: dict, clip_max: float = MAX_SINGLE_EVENT_SEC):
    dur = float(ev.get("duration", 0))
    if dur <= 0:
        return None
    if clip_max and dur > clip_max:
        dur = clip_max
    ts_str = ev["timestamp"].replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts_str).astimezone()
    start_ts = dt.timestamp()
    return (start_ts, start_ts + dur, ev.get("data", {}))


def merge_intervals(intervals):
    if not intervals:
        return []
    sorted_iv = sorted(intervals, key=lambda x: x[0])
    merged = [list(sorted_iv[0][:2])]
    for start, end, *_ in sorted_iv[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def intersect_events_with_mask(events, mask_intervals):
    if not events or not mask_intervals:
        return []
    events_sorted = sorted(events, key=lambda x: x[0])
    result = []
    j = 0
    m = len(mask_intervals)
    for ev_start, ev_end, data in events_sorted:
        while j < m and mask_intervals[j][1] <= ev_start:
            j += 1
        k = j
        while k < m and mask_intervals[k][0] < ev_end:
            s = max(ev_start, mask_intervals[k][0])
            e = min(ev_end, mask_intervals[k][1])
            if e > s:
                result.append((s, e, data))
            k += 1
    return result


def event_end_local_datetime(ev: dict):
    """Return an event's local end time for collection-coverage diagnostics."""
    ts = ev.get("timestamp")
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone()
        duration = max(0.0, float(ev.get("duration", 0) or 0))
        return dt + timedelta(seconds=duration)
    except (TypeError, ValueError, OverflowError):
        return None


def summarize_data_coverage(raw_events: dict):
    """Summarize the newest event in each watcher group without inventing data."""
    coverage = {}
    for group, events in raw_events.items():
        newest = max(
            (event_end_local_datetime(event) for event in events),
            default=None,
        )
        coverage[group] = {
            "eventCount": len(events),
            "latestEvent": newest.isoformat(timespec="seconds") if newest else None,
        }
        latest_text = newest.strftime("%Y-%m-%d %H:%M:%S") if newest else "无事件"
        print(f"[AW] 桶组 {group}: {len(events):,} 条事件，最新结束时间 {latest_text}")
    return coverage


def fetch_all_events(year: int):
    resp = requests.get(f"{AW_API_BASE}/buckets/")
    resp.raise_for_status()
    buckets = resp.json()

    target_buckets = {"window": [], "afk": [], "input": [], "web": []}
    for b_id in buckets:
        b_lower = b_id.lower()
        if "aw-watcher-window" in b_lower:
            target_buckets["window"].append(b_id)
        elif "aw-watcher-afk" in b_lower:
            target_buckets["afk"].append(b_id)
        elif "aw-watcher-input" in b_lower:
            target_buckets["input"].append(b_id)
        elif "aw-watcher-web" in b_lower:
            target_buckets["web"].append(b_id)

    local_tz = datetime.now().astimezone().tzinfo
    start_dt = datetime(year, 1, 1, 0, 0, 0, tzinfo=local_tz)
    end_dt = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=local_tz)

    raw_events = {"window": [], "afk": [], "input": [], "web": []}
    for key, b_list in target_buckets.items():
        for b_id in b_list:
            print(f"[AW] 正在读取桶 {b_id} ({year} 全年)...")
            r = requests.get(
                f"{AW_API_BASE}/buckets/{b_id}/events",
                params={"start": start_dt.isoformat(), "end": end_dt.isoformat(), "limit": -1},
            )
            r.raise_for_status()
            raw_events[key].extend(r.json())
    return raw_events


def analyze():
    (
        compiled_rules, _, candidate_macro_groups, category_to_candidate_macro,
        candidate_fallback_macro_id,
    ) = load_category_rules()
    raw_events = fetch_all_events(TARGET_YEAR)
    bucket_coverage = summarize_data_coverage(raw_events)

    not_afk_raw, afk_raw = [], []
    for ev in raw_events["afk"]:
        parsed = parse_event_interval(ev, clip_max=12 * 3600)
        if not parsed:
            continue
        s, e, d = parsed
        if d.get("status") == "not-afk":
            not_afk_raw.append((s, e))
        elif d.get("status") == "afk":
            afk_raw.append((s, e))

    not_afk_mask = merge_intervals(not_afk_raw)
    afk_mask = merge_intervals(afk_raw)

    web_events = sorted(
        [p for ev in raw_events["web"] if (p := parse_event_interval(ev))],
        key=lambda x: x[0]
    )
    win_events = [p for ev in raw_events["window"] if (p := parse_event_interval(ev))]
    active_windows = sorted(intersect_events_with_mask(win_events, not_afk_mask), key=lambda x: x[0])
    zombie_windows = intersect_events_with_mask(win_events, afk_mask)

    # 第一步先给前台窗口分类并累计候选分类时长，之后才能判断哪些子分类值得单独展示。
    web_idx = 0
    web_len = len(web_events)
    provisional_windows = []
    provisional_usage_sec = defaultdict(float)

    for s, e, d in active_windows:
        app = prettify_name(d.get("app") or "Unknown")
        title = (d.get("title") or "").strip()
        match_text = f"{d.get('app', '')} {title}"

        if "firefox" in app.lower():
            mid = (s + e) / 2.0
            while web_idx < web_len and web_events[web_idx][1] < mid:
                web_idx += 1
            if web_idx < web_len and web_events[web_idx][0] <= mid <= web_events[web_idx][1]:
                w_data = web_events[web_idx][2]
                match_text += f" {w_data.get('title', '')} {w_data.get('url', '')}"

        cat_id, kw = match_category(match_text, compiled_rules, None)
        candidate_macro_id = category_to_candidate_macro.get(
            cat_id, candidate_fallback_macro_id
        )
        entity_name = kw if kw != "Uncategorized" else app
        provisional_windows.append((s, e, entity_name, candidate_macro_id))
        provisional_usage_sec[candidate_macro_id] += (e - s)

    macro_groups, candidate_to_final_macro, fallback_macro_id, kept_child_ids = collapse_macro_groups(
        candidate_macro_groups,
        provisional_usage_sec,
        max_groups=MAX_MACRO_GROUPS,
        min_child_share=MIN_CHILD_CATEGORY_SHARE,
    )
    macro_ids = sorted(macro_groups)
    macro_count = len(macro_groups)
    resolved_active_windows = [
        (s, e, entity_name, candidate_to_final_macro.get(candidate_macro_id, fallback_macro_id))
        for s, e, entity_name, candidate_macro_id in provisional_windows
    ]

    def child_share_percent(candidate_child_id):
        parent_id = candidate_macro_groups[candidate_child_id].get("parent_id")
        parent_total = provisional_usage_sec.get(parent_id, 0.0) + sum(
            provisional_usage_sec.get(cid, 0.0)
            for cid, meta in candidate_macro_groups.items()
            if meta.get("parent_id") == parent_id
        )
        child_total = provisional_usage_sec.get(candidate_child_id, 0.0)
        return child_total / parent_total * 100.0 if parent_total > 0 else 0.0

    kept_child_labels = [
        f"{candidate_macro_groups[mid]['label']} ({child_share_percent(mid):.1f}%)"
        for mid in sorted(kept_child_ids)
    ]
    print(
        f"[分类] 最终保留 {macro_count}/{MAX_MACRO_GROUPS} 个统计类型；"
        f"子分类独立展示门槛：所属母类时长占比 ≥ {MIN_CHILD_CATEGORY_SHARE:.0%}；"
        f"独立展示的子分类：{('、'.join(kept_child_labels)) if kept_child_labels else '无'}"
    )
    for candidate_id, final_id in sorted(candidate_to_final_macro.items()):
        if candidate_id not in kept_child_ids and candidate_macro_groups[candidate_id].get("parent_id") is not None:
            if candidate_id != final_id:
                print(
                    f"[分类] 子分类「{candidate_macro_groups[candidate_id]['label']}」"
                    f"并入母分类「{macro_groups[final_id]['label']}」"
                )

    daily_stats = defaultdict(lambda: {
        "active_sec": 0.0,
        "macro_sec": defaultdict(float),
        "item_sec": defaultdict(float),
        "presses": 0,
        "clicks": 0,
        "dist_m": 0.0,
        "scroll_m": 0.0,
        "max_tabs": 0,
    })
    macro_total_sec = defaultdict(float)
    monthly_macro_sec = [[0.0 for _ in range(macro_count + 1)] for _ in range(12)]
    hourly_macro_sec = [[0.0 for _ in range(macro_count + 1)] for _ in range(24)]
    monthly_input = [{"presses": 0, "clicks": 0, "distKm": 0.0, "scrollM": 0.0} for _ in range(12)]

    app_stats = defaultdict(lambda: {
        "active_sec": 0.0, "afk_sec": 0.0, "presses": 0, "clicks": 0,
        "macro_id": fallback_macro_id
    })

    for s, e, entity_name, macro_id in resolved_active_windows:
        dur = e - s
        dt = datetime.fromtimestamp(s).astimezone()
        date_str = dt.strftime("%Y-%m-%d")

        daily_stats[date_str]["active_sec"] += dur
        daily_stats[date_str]["macro_sec"][macro_id] += dur
        if entity_name not in EXCLUDED_ENTITIES and entity_name != "Firefox":
            daily_stats[date_str]["item_sec"][entity_name] += dur

        macro_total_sec[macro_id] += dur
        monthly_macro_sec[dt.month - 1][macro_id] += dur / 3600.0
        hourly_macro_sec[dt.hour][macro_id] += dur / 3600.0

        app_stats[entity_name]["active_sec"] += dur
        app_stats[entity_name]["macro_id"] = macro_id

    for s, e, d in zombie_windows:
        dur = e - s
        app = prettify_name(d.get("app") or "Unknown")
        title = (d.get("title") or "").strip()
        cat_id, kw = match_category(
            f"{d.get('app', '')} {title}", compiled_rules, None
        )
        entity_name = kw if kw != "Uncategorized" else app
        if entity_name in app_stats:
            app_stats[entity_name]["afk_sec"] += dur

    input_events = []
    for ev in raw_events["input"]:
        d = ev.get("data", {})
        presses, clicks = int(d.get("presses", 0)), int(d.get("clicks", 0))
        dx, dy = float(d.get("deltaX", 0)), float(d.get("deltaY", 0))
        sx, sy = float(d.get("scrollX", 0)), float(d.get("scrollY", 0))
        if presses == 0 and clicks == 0 and dx == 0 and dy == 0 and sx == 0 and sy == 0:
            continue
        parsed = parse_event_interval(ev, clip_max=300)
        if parsed:
            input_events.append((parsed[0], parsed[1], {
                "presses": presses, "clicks": clicks,
                "dist_counts": math.hypot(dx, dy),
                "dx": abs(dx), "dy": abs(dy),
                "scroll_ticks": abs(sx) + abs(sy),
            }))

    input_sorted = sorted(input_events, key=lambda x: x[0])
    total_presses = total_clicks = 0
    total_dist_counts = total_dx = total_dy = total_scroll_ticks = 0.0

    w_idx = 0
    w_len = len(resolved_active_windows)
    for s, e, inp in input_sorted:
        dt = datetime.fromtimestamp(s).astimezone()
        date_str = dt.strftime("%Y-%m-%d")
        dist_m = inp["dist_counts"] / COUNTS_PER_METER
        scroll_m = inp["scroll_ticks"] * SCROLL_METERS_PER_TICK

        daily_stats[date_str]["presses"] += inp["presses"]
        daily_stats[date_str]["clicks"] += inp["clicks"]
        daily_stats[date_str]["dist_m"] += dist_m
        daily_stats[date_str]["scroll_m"] += scroll_m

        m_idx = dt.month - 1
        monthly_input[m_idx]["presses"] += inp["presses"]
        monthly_input[m_idx]["clicks"] += inp["clicks"]
        monthly_input[m_idx]["distKm"] += dist_m / 1000.0
        monthly_input[m_idx]["scrollM"] += scroll_m

        total_presses += inp["presses"]
        total_clicks += inp["clicks"]
        total_dist_counts += inp["dist_counts"]
        total_dx += inp["dx"]
        total_dy += inp["dy"]
        total_scroll_ticks += inp["scroll_ticks"]

        mid_ts = (s + e) / 2.0
        while w_idx < w_len and resolved_active_windows[w_idx][1] < mid_ts:
            w_idx += 1
        if w_idx < w_len and resolved_active_windows[w_idx][0] <= mid_ts <= resolved_active_windows[w_idx][1]:
            entity_name = resolved_active_windows[w_idx][2]
            app_stats[entity_name]["presses"] += inp["presses"]
            app_stats[entity_name]["clicks"] += inp["clicks"]

    daily_tabs = defaultdict(list)
    peak_tab_record = {"maxTabs": 0, "date": "", "time": "", "title": ""}

    for s, e, d in web_events:
        tab_count = int(d.get("tabCount") or 0)
        dt = datetime.fromtimestamp(s).astimezone()
        date_str = dt.strftime("%Y-%m-%d")
        if tab_count > 0:
            daily_tabs[date_str].append((tab_count, e - s))
            if tab_count > daily_stats[date_str]["max_tabs"]:
                daily_stats[date_str]["max_tabs"] = tab_count
            if tab_count > peak_tab_record["maxTabs"]:
                peak_tab_record = {
                    "maxTabs": tab_count,
                    "date": date_str,
                    "time": dt.strftime("%H:%M"),
                    "title": strip_domain_from_title(d.get("title") or ""),
                }

    calendar_records = []
    for date_str in sorted(daily_stats.keys()):
        st = daily_stats[date_str]
        sorted_macros = sorted(st["macro_sec"].items(), key=lambda x: x[1], reverse=True)
        top_macro = sorted_macros[0][0] if sorted_macros else fallback_macro_id
        top_item = max(st["item_sec"].items(), key=lambda x: x[1])[0] if st["item_sec"] else "日常浏览"
        calendar_records.append({
            "date": date_str,
            "activeHours": round(st["active_sec"] / 3600.0, 2),
            "topMacro": top_macro,
            "topItem": top_item,
            "presses": st["presses"],
            "clicks": st["clicks"],
            "distMeters": round(st["dist_m"], 1),
            "scrollMeters": round(st["scroll_m"], 1),
            "maxTabs": st["max_tabs"],
        })

    pie_summary = [
        {
            "id": macro_id,
            "name": macro_groups[macro_id]["label"],
            "color": macro_groups[macro_id]["color"],
            "hours": round(macro_total_sec[macro_id] / 3600.0, 1),
        }
        for macro_id in macro_ids
        if macro_total_sec[macro_id] > 300
    ]

    all_valid_entities = []
    for name, st in sorted(app_stats.items(), key=lambda x: x[1]["active_sec"], reverse=True):
        if name in EXCLUDED_ENTITIES or name.lower() in {"game", "uncategorized", "unknown"}:
            continue
        active_min = st["active_sec"] / 60.0
        if active_min < 20:
            continue
        total_fg = st["active_sec"] + st["afk_sec"]
        all_valid_entities.append({
            "name": name,
            "macroId": st["macro_id"],
            "activeHours": round(st["active_sec"] / 3600.0, 1),
            "afkHours": round(st["afk_sec"] / 3600.0, 1),
            "afkRate": round(st["afk_sec"] / total_fg * 100, 1) if total_fg > 0 else 0,
            "kpm": round(st["presses"] / active_min, 1),
            "cpm": round(st["clicks"] / active_min, 1),
        })

    entities_summary = all_valid_entities[:20]
    selected_names = {e["name"] for e in entities_summary}
    high_apm_outliers = sorted(
        [
            e for e in all_valid_entities
            if e["name"] not in selected_names
            and e["macroId"] != fallback_macro_id
            and (e["kpm"] >= 90 or e["cpm"] >= 20)
        ],
        key=lambda x: x["kpm"],
        reverse=True
    )
    for outlier in high_apm_outliers[:4]:
        entities_summary.append(outlier)

    tabs_trend = []
    for date_str in sorted(daily_tabs.keys()):
        recs = daily_tabs[date_str]
        tw = sum(w for _, w in recs)
        avg_t = sum(t * w for t, w in recs) / tw if tw > 0 else 0
        tabs_trend.append({"date": date_str, "avgTabs": round(avg_t, 1), "maxTabs": max(t for t, _ in recs)})

    total_dist_km = (total_dist_counts / COUNTS_PER_METER) / 1000.0
    total_scroll_m = total_scroll_ticks * SCROLL_METERS_PER_TICK

    payload = {
        "year": TARGET_YEAR,
        "dataCoverage": {
            "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "latestActivityDate": calendar_records[-1]["date"] if calendar_records else None,
            "latestBrowserDate": tabs_trend[-1]["date"] if tabs_trend else None,
            "buckets": bucket_coverage,
        },
        "overview": {
            "totalActiveHours": round(sum(r["activeHours"] for r in calendar_records), 1),
            "totalPresses": total_presses,
            "totalClicks": total_clicks,
            "mouseDistKm": round(total_dist_km, 2),
            "xyRatio": round(total_dx / total_dy, 2) if total_dy > 0 else 1.0,
            "scrollMeters": round(total_scroll_m, 1),
            "threeBodySets": round((total_presses / 3.8) / 880000, 2),
            "fingerLiftTons": round((total_presses * KEY_FORCE_KG) / 1000.0, 2),
            "marathons": round(total_dist_km / 42.195, 2),
            "everests": round(total_scroll_m / 8848.86, 2),
        },
        "calendar": calendar_records,
        "macroGroups": [
            {"id": macro_id, **macro_groups[macro_id]}
            for macro_id in macro_ids
        ],
        "macroPie": pie_summary,
        "monthlyStream": [
            {
                "id": macro_id,
                "name": macro_groups[macro_id]["label"],
                "color": macro_groups[macro_id]["color"],
                "data": [round(monthly_macro_sec[month][macro_id], 1) for month in range(12)],
            }
            for macro_id in macro_ids
        ],
        "hourlyTide": [
            {
                "id": macro_id,
                "name": macro_groups[macro_id]["label"],
                "color": macro_groups[macro_id]["color"],
                "data": [round(hourly_macro_sec[hour][macro_id], 1) for hour in range(24)],
            }
            for macro_id in macro_ids
            if not macro_groups[macro_id]["is_uncategorized"]
        ],
        "monthlyInput": [
            {
                "pressesWan": round(m["presses"] / 10000.0, 2),
                "clicksWan": round(m["clicks"] / 10000.0, 2),
                "distKm": round(m["distKm"], 2),
                "scrollM": round(m["scrollM"], 1),
            }
            for m in monthly_input
        ],
        "entities": entities_summary,
        "firefox": {
            "tabsTrend": tabs_trend,
            "peakMoment": peak_tab_record,
        },
    }

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"✅ 已生成更新版数据文件: {os.path.abspath(OUTPUT_JSON_PATH)}")
    latest_activity = calendar_records[-1]["date"] if calendar_records else "无活动记录"
    latest_browser = tabs_trend[-1]["date"] if tabs_trend else "无浏览器记录"
    print(f"[AW] 日历活动数据截至: {latest_activity}")
    print(f"[AW] 浏览器标签页数据截至: {latest_browser}")
    if latest_activity and latest_activity != "无活动记录":
        try:
            latest_day = datetime.strptime(latest_activity, "%Y-%m-%d").date()
            today = datetime.now().astimezone().date()
            if latest_day < today:
                print("[WARN] 最新活动日期早于今天：请检查上方各 watcher 桶的最新事件时间；若桶组也停在该日期，需先恢复对应 ActivityWatch watcher。")
        except ValueError:
            pass


if __name__ == "__main__":
    analyze()