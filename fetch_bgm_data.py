import requests
import re
import json
import time
import concurrent.futures
from datetime import datetime

# --- 用户配置 ---
USER_ID = ''                    # 替换你的 ID
USER_AGENT = ''                 # 替换为你的 User-Agent，参见 https://github.com/bangumi/api/blob/master/docs-raw/user%20agent.md
USER_TOKEN = ''                 # 可留空，为了访问 NSFW 条目
COLLECTION_TYPE = 2             # 2 = 看过
TARGET_COLLECTION_YEAR = 2026   # 填 None 表示全部
CONCURRENCY = 8                 # 并发数
OUTPUT_FILE = f'bgm-collection-data-{TARGET_COLLECTION_YEAR}.json'

# --- 排除列表 (比如当年补标的条目) ---
EXCLUDE_SUBJECT_IDS = [
    188091, 428735, 218711, 58850, 295017, 172498, 
    290, 227245, 260772, 181995, 235612, 36004, 425211
]

API_BASE = 'https://api.bgm.tv/v0'
HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'application/json',
    'Authorization': f'Bearer {USER_TOKEN}'
}


def api_request(url, params=None):
    """通用请求函数 (带重试)"""
    retries = 3
    for i in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=10)
            if response.status_code == 404: return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if i == retries - 1:
                print(f"[Error] {url}: {e}")
                return None
            time.sleep(1)

def fetch_user_collections(username, subject_type=2, collection_type=2, target_year=None):
    """获取收藏列表 (含年份剪枝和黑名单过滤)"""
    print(f"正在获取用户 {username} 的收藏列表...")
    items = []
    limit = 100
    offset = 0
    has_more = True
    
    while has_more:
        url = f"{API_BASE}/users/{username}/collections"
        data = api_request(url, {'subject_type': subject_type, 'type': collection_type, 'limit': limit, 'offset': offset})
        
        if not data or not data.get('data'): break
        
        batch = data['data']
        for item in batch:
            sid = item['subject_id']
            
            # 1. 黑名单过滤
            if sid in EXCLUDE_SUBJECT_IDS:
                continue

            # 2. 收藏年份过滤 (updated_at)
            updated_at = item.get('updated_at')
            if target_year is not None and updated_at:
                try:
                    y = int(updated_at[:4])
                    if y > target_year: continue # 还没到目标年份 (因为倒序)
                    if y < target_year: 
                        has_more = False # 已经过了目标年份，停止
                        break
                except: pass
            
            # 保留基本信息，后续补充详情
            items.append({
                'subject_id': sid,
                'updated_at': updated_at,
                'comment': item.get('comment'),
                'rate': item.get('rate')
            })
            
        if len(batch) < limit or not has_more: break
        offset += limit
        print(f"  已扫描 {offset} 条，命中 {len(items)} 条...")
        time.sleep(0.5)

    print(f"符合条件的条目数: {len(items)}")
    return items

def fetch_details(basic_info):
    """
    获取单个条目的所有详细信息:
    1. Subject Info (Title, Date, Tags, Infobox)
    2. Episodes (Total Duration) - 混合时长获取逻辑 (API > Infobox片长 > 默认值)
    3. Persons (Studios, Directors)
    4. Characters (Main Actors)
    """
    sid = basic_info['subject_id']
    
    # A. 基础详情
    info = api_request(f"{API_BASE}/subjects/{sid}")
    tags = info.get('meta_tags', []) if info else []
    
    # --- 1. 确定兜底的默认时长 (Fallback Duration) ---
    # 逻辑：先根据Tag定一个基准，如果是剧场版，尝试从 Infobox 修正这个基准
    
    fallback_duration = 0
    is_movie = '剧场版' in tags
    
    if is_movie:
        # 默认剧场版 100分钟
        fallback_duration = 100 * 60 
        
        # 尝试从 Infobox 获取 "片长"
        if info and 'infobox' in info:
            for item in info['infobox']:
                if item.get('key') == '片长':
                    val = item.get('value', '')
                    # 使用正则提取数字，例如 "114分" -> 114
                    match = re.search(r'(\d+)', str(val))
                    if match:
                        minutes = int(match.group(1))
                        fallback_duration = minutes * 60
                    break
                    
    elif 'TV' in tags or 'OAD' in tags:
        fallback_duration = 25 * 60   # 1500秒
    elif 'OVA' in tags:
        fallback_duration = 10 * 60   # 600秒 (有的 OVA 是 TV 时长，有的 OVA 是短篇时长，取中间值)
    elif 'WEB' in tags:
        fallback_duration = 5 * 60    # 300秒
    
    # B. 剧集时长 (累加)
    total_seconds = 0
    ep_offset = 0
    
    while True:
        ep_data = api_request(f"{API_BASE}/episodes", {'subject_id': sid, 'limit': 100, 'offset': ep_offset})
        if not ep_data or not ep_data.get('data'): break
        
        for ep in ep_data['data']:
            # 过滤非正片 (type 0=本篇, 1=SP, 2=OP/ED)
            # 通常我们只统计本篇，或者根据你的需求统计所有。这里默认统计 type=0 (本篇)
            if ep.get('type') != 0:
                continue

            dur = ep.get('duration_seconds', 0)
            
            if dur > 0:
                total_seconds += dur
            else:
                # 剧集没有时长数据，使用计算好的 fallback
                if fallback_duration > 0:
                    total_seconds += fallback_duration
                else:
                    # 既无API数据，Tag也不符合三大类，警告
                    ep_sort = ep.get('sort', '?')
                    title = info.get('name_cn') or info.get('name') or 'Unknown'
                    print(f"[Warning] ID:{sid}《{title}》ep.{ep_sort} 无时长且无法通过Tag推断默认值")
        
        if len(ep_data['data']) < 100: break
        ep_offset += 100

    # 特殊情况处理：
    # 有些条目可能没有 episodes 数据（例如 API 还没录入 ep 信息），但它是剧场版
    # 这种情况下上面的循环可能一次都没执行，导致 total_seconds 为 0
    if total_seconds == 0 and is_movie and fallback_duration > 0:
        total_seconds = fallback_duration

    # C. 制作人员 (Studio & Director)
    studios = []
    directors = []
    persons = api_request(f"{API_BASE}/subjects/{sid}/persons") or []
    for p in persons:
        rel = p.get('relation', '')
        if rel == '动画制作': 
            studios.append(p.get('name'))
        if rel in ['导演', '总导演']: 
            directors.append(p.get('name'))

    # D. 主角声优 (Actors)
    actors = []
    chars = api_request(f"{API_BASE}/subjects/{sid}/characters") or []
    for c in chars:
        if c.get('relation') == '主角':
            for actor in c.get('actors', []):
                name = actor.get('name')
                # 去重添加
                if name and name not in actors:
                    actors.append(name)

    # E. 组装最终对象
    return {
        'id': sid,
        'title': info.get('name_cn') or info.get('name') or 'Unknown',
        'date': info.get('date', ''),
        'updated_at': basic_info['updated_at'],
        'rate': basic_info['rate'],
        'tags': tags,
        'duration': total_seconds,
        'studios': studios,
        'directors': directors,
        'actors': actors
    }

def main():
    # 1. 获取列表
    raw_list = fetch_user_collections(USER_ID, COLLECTION_TYPE, COLLECTION_TYPE, TARGET_COLLECTION_YEAR)
    if not raw_list: return

    # 2. 并发获取详情
    print(f"开始抓取 {len(raw_list)} 个条目的详细信息...")
    final_data = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(fetch_details, item) for item in raw_list]
        completed = 0
        for f in concurrent.futures.as_completed(futures):
            try:
                res = f.result()
                final_data.append(res)
            except Exception as e:
                print(f"Error processing item: {e}")
            
            completed += 1
            if completed % 5 == 0:
                print(f"进度: {completed}/{len(raw_list)}")

    # 3. 输出纯 JSON
    output = {
        'meta': {
            'user': USER_ID,
            'generated_at': datetime.now().isoformat(),
            'target_year': TARGET_COLLECTION_YEAR,
            'count': len(final_data)
        },
        'data': final_data
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"成功! 原始数据已保存至 {OUTPUT_FILE} (大小: {len(final_data)} 条目)")


if __name__ == '__main__':
    main()
    # 获取json文件
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # 统计时长，转格式为xx天xx小时xx分钟xx秒
        total_duration = sum(item['duration'] for item in data['data'])
        days, remainder = divmod(total_duration, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"总时长: {days}天 {hours}小时 {minutes}分钟 {seconds}秒")