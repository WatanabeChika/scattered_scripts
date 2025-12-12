import requests
import time
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
    
    # 配置重试策略：最大重试3次，退避系数0.5（即间隔时间会增加）
    # 这里主要处理连接层面的错误
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    # 添加 User-Agent，伪装成浏览器，防止被服务器主动拒绝
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0"
    }

    print(f"开始抓取，预计发送 {total_requests} 次请求...")

    for t in types:
        for s in sources:
            count += 1
            params = {
                'type': t,
                'source': s
            }
            
            # 手动实现业务层面的重试逻辑（针对 ReadTimeout 等）
            max_attempts = 3
            success = False
            
            for attempt in range(1, max_attempts + 1):
                try:
                    if attempt == 1:
                        print(f"[{count}/{total_requests}] 正在获取: type={t}, source={s}")
                    else:
                        print(f"[{count}/{total_requests}] 重试第 {attempt-1} 次: type={t}, source={s}")
                    
                    # 发送 GET 请求，设置超时时间延长至 30 秒
                    response = session.get(base_url, params=params, headers=headers, timeout=30)
                    
                    # 检查响应状态码
                    if response.status_code == 200:
                        data = response.json()
                        
                        current_batch_count = 0
                        # 遍历数据提取 ID
                        for category_list in data.values():
                            if isinstance(category_list, list):
                                for card in category_list:
                                    if 'id' in card:
                                        unique_ids.add(card['id'])
                                        current_batch_count += 1
                        
                        print(f"    - 成功获取，本批次包含 {current_batch_count} 个ID")
                        success = True
                        break # 成功则跳出重试循环
                    else:
                        print(f"    - 请求失败，状态码: {response.status_code}")
                
                except requests.exceptions.Timeout:
                    print(f"    - 请求超时 (Attempt {attempt})")
                except requests.exceptions.RequestException as e:
                    print(f"    - 请求发生错误: {e}")
                
                # 如果不是最后一次尝试，稍作等待再重试
                if attempt < max_attempts:
                    time.sleep(3)
            
            if not success:
                print(f"!!! 警告: type={t}, source={s} 在 {max_attempts} 次尝试后仍然失败，已跳过。")
            
            # 批次之间的礼貌性延时，防止 IP 被封
            time.sleep(2)

    # 将集合转换为列表并排序
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
        fetch_and_extract_ids()
    except ImportError:
        print("错误: 缺少必要的库，请检查环境。")
    except Exception as e:
        print(f"脚本运行期间发生未捕获的异常: {e}")