import requests
import time
import json

def fetch_and_extract_ids():
    base_url = "https://sapi.moecube.com:444/ygopro/analytics/single/type"
    
    # 定义所有参数选项
    types = ['day', 'week', 'halfmonth', 'month', 'season']
    sources = [
        'mycard-athletic', '233-athletic', 
        'mycard-entertain', '233-entertain', 
        'mycard-custom', '233-custom', 
        'mycard-tag', '233-tag'
    ]
    
    # 使用集合(set)来存储ID，自动去重
    unique_ids = set()
    
    total_requests = len(types) * len(sources)
    count = 0
    
    print(f"开始抓取，预计发送 {total_requests} 次请求...")

    for t in types:
        for s in sources:
            count += 1
            params = {
                'type': t,
                'source': s
            }
            
            try:
                print(f"[{count}/{total_requests}] 正在获取: type={t}, source={s}")
                
                # 发送 GET 请求，设置超时时间
                response = requests.get(base_url, params=params, timeout=10)
                
                # 检查响应状态码
                if response.status_code == 200:
                    data = response.json()
                    
                    # 根据你提供的 JSON 结构，数据按 'monster', 'spell', 'trap', 'side', 'ex' 分类
                    # 我们遍历这些 key 对应的列表
                    for category_list in data.values():
                        if isinstance(category_list, list):
                            for card in category_list:
                                # 提取 id 并加入集合
                                if 'id' in card:
                                    unique_ids.add(card['id'])
                else:
                    print(f"请求失败，状态码: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"请求发生错误: {e}")
            
            # 重要：设置延时，防止 IP 被封 (设置为2秒)
            time.sleep(2)

    # 将集合转换为列表并排序（可选）
    final_id_list = sorted(list(unique_ids))
    
    print("-" * 30)
    print(f"抓取完成。")
    print(f"共去重后得到 {len(final_id_list)} 个唯一的 ID。")
    
    # 保存结果到文件
    output_filename = "common_cards.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(final_id_list, f, ensure_ascii=False)
        
    print(f"结果已保存至: {output_filename}")

if __name__ == "__main__":
    try:
        import requests
        fetch_and_extract_ids()
    except ImportError:
        print("错误: 未找到 requests 库。请运行 'pip install requests' 进行安装。")