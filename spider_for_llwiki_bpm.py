import requests
from lxml import etree
import pandas as pd
import time
import json
import matplotlib.pyplot as plt

main_url = 'https://llwiki.org'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'}

def get_html(url):
    time.sleep(0.7)
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print('Error:', response.status_code)
        exit(1)
    return response.text

def get_groups(url):
    html = get_html(url)
    root = etree.HTML(html)
    divs = root.xpath('//div[@class="mw-category-group"]')
    for d in divs:
        t = d.xpath('./h3/text()')[0]
        if t == 'L':
            items = d.xpath('./ul/li//a/@href')
            return items

def get_songs(url):
    html = get_html(url)
    root = etree.HTML(html)
    divs = root.xpath('//div[@class="mw-category-group"]')
    items = []
    titles = []
    for i in range(len(divs)):
        if i == 0:
            continue
        d = divs[i]
        items.extend(d.xpath('./ul/li//a/@href'))
        titles.extend(d.xpath('./ul/li//a/text()'))
    return items, titles

def get_bpm(url):
    html = get_html(url)
    root = etree.HTML(html)
    infotable = root.xpath('//table[@class="infoboxtemplate"]')[0]
    info = ['NO_TITLE', 'NO_BPM']
    for tr in infotable.xpath('./tbody/tr'):
        ths = ''.join(tr.xpath('./th//text()[not(ancestor::style)]'))
        if ths.strip() == '歌曲原名':
            info[0] = ''.join(tr.xpath('./td//text()')).strip()
        if ths.strip() == 'BPM':
            info[1] = ''.join(tr.xpath('./td//text()')).strip()
    return info

def get_all_bpm():
    origin_url = main_url + '/zh/Category:%E6%AD%8C%E6%9B%B2'
    groups = get_groups(origin_url)
    titles = []
    bpm = []
    for g in groups:
        songs, songnames = get_songs(main_url + g)
        titles.extend(songnames)
        for s in songs:
            info = get_bpm(main_url + s)
            print(info)
            bpm.append(info[1])
    data = {
        'title': titles,
        'bpm': bpm
    }
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def data_process():
    with open('data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    
    no_bpm = df[df['bpm'] == 'NO_BPM']
    trans_bpm = df[df['bpm'].str.contains('→') | df['bpm'].str.contains('〜')]
    valid_df = df[(df['bpm'] != 'NO_BPM') & (~df['bpm'].str.contains('→')) & (~df['bpm'].str.contains('〜'))]
    walk_bpm = valid_df[(valid_df['bpm'].astype(int) > 110) & (valid_df['bpm'].astype(int) < 130)]
    run_bpm = valid_df[(valid_df['bpm'].astype(int) > 160) & (valid_df['bpm'].astype(int) < 180)]

    dic = {}
    dic['暂无bpm'] = [no_bpm['title'].tolist()]
    dic['变bpm'] = [trans_bpm['title'].tolist(), trans_bpm['bpm'].tolist()]
    dic['110 < bpm < 130'] = [walk_bpm['title'].tolist(), walk_bpm['bpm'].tolist()]
    dic['160 < bpm < 180'] = [run_bpm['title'].tolist(), run_bpm['bpm'].tolist()]
    
    with open('result.json', 'w', encoding='utf-8') as f:
        json.dump(dic, f, ensure_ascii=False, indent=2)
    
def draw_bpm():
    plt.rcParams['font.family'] = 'Source Han Sans JP'
    with open('result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    walk = data['110 < bpm < 130']
    run = data['160 < bpm < 180']
    walk_df = pd.DataFrame({'title': walk[0], 'bpm': walk[1]})
    run_df = pd.DataFrame({'title': run[0], 'bpm': run[1]})
    walk_df['bpm'] = walk_df['bpm'].astype(int)
    run_df['bpm'] = run_df['bpm'].astype(int)
    walk_df = walk_df.sort_values(by='bpm')
    run_df = run_df.sort_values(by='bpm')
    plt.figure(figsize=(10, 20))
    plt.barh(walk_df['title'], walk_df['bpm'], color='skyblue')
    plt.title('110 < bpm < 130')
    plt.xlim(100, 135)
    for a, b in zip(walk_df['bpm'], range(len(walk_df))):
        plt.text(a, b, a, ha='left', va='center', fontsize=10)
    plt.tight_layout()
    plt.savefig('bpm1.png')
    plt.figure(figsize=(10, 20))
    plt.barh(run_df['title'], run_df['bpm'], color='orange')
    plt.title('160 < bpm < 180')
    plt.xlim(150, 185)
    for a, b in zip(run_df['bpm'], range(len(run_df))):
        plt.text(a, b, a, ha='left', va='center', fontsize=10)
    plt.tight_layout()
    # save the figure
    plt.savefig('bpm2.png')

if __name__ == '__main__':
    # get_all_bpm()
    # data_process()
    draw_bpm()