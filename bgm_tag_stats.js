// ==UserScript==
// @name         Bangumi 标签统计分析
// @version      1.1.0
// @description  统计 Bangumi 用户收藏的标签分布
// @author       WatanabeChika
// @match        *://bgm.tv/user/*
// @match        *://bangumi.tv/user/*
// @match        *://chii.in/user/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // --- 库加载器 ---
    function loadChartJS(callback) {
        if (typeof Chart !== 'undefined') {
            return callback();
        }
        
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
        
        script.onload = callback;
        script.onerror = () => console.error("Failed to load Chart.js dependency.");
        
        document.head.appendChild(script);
    }
    
    function mainAppLogic() {
        
        // --- 配置 ---
        const API_BASE = 'https://api.bgm.tv/v0';
        const CONCURRENCY_LIMIT = 10; 
        const RETRY_DELAY = 100; 
        const MIN_PERCENTAGE = 0.02; 
        const PREF_KEY = 'bgm_stats_prefs'; // 用于保存开关状态
    
        // --- 字典 ---
        // 注意：年份是动态的，不在此字典定义，但需要在此占位以便逻辑统一
        const animeFilterDict = {
            category: ['TV', 'WEB', 'OVA', '剧场版', '动态漫画', '其他'],
            source: ['原创', '漫画改', '游戏改', '小说改', '影视改'],
            type: ['科幻', '喜剧', '同人', '百合', '校园', '惊悚', '后宫',
                   '机战', '悬疑', '恋爱', '奇幻', '推理', '运动', '耽美', '音乐',
                   '战斗', '冒险', '萌系', '穿越', '玄幻', '乙女', '恐怖', '历史',
                   '日常', '剧情', '武侠', '美食', '职场']
            // 'year' 字段将在运行时动态生成
        };
    
        const titleMap = {
            category: '分类',
            source: '来源',
            type: '类型',
            year: '放送年份'
        };
    
        // --- 主题色逻辑 ---
        const themeColors = {
            'pink': '#f09199',
            'blue': '#00a2d4',
            'orange': '#f58231',
            'green': '#3cb44b',
            'default': '#f09199'
        };
    
        function getCurrentAccentColor() {
            const themeAttr = document.documentElement.getAttribute('data-theme-color') || 'pink';
            return themeColors[themeAttr] || themeColors['default'];
        }
        
        // --- 设置CSS变量 ---
        const accentColor = getCurrentAccentColor();
        document.documentElement.style.setProperty('--bgm-accent', accentColor);
    
    
        // --- 缓存与偏好管理 ---
        const CACHE_KEY_PREFIX = 'bgm_stats_cache_';
        
        function getCache(username, type, year) {
            const key = `${CACHE_KEY_PREFIX}${username}_${type}_${year}`;
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : null;
        }
    
        function setCache(username, type, year, data, totalCount) {
            const key = `${CACHE_KEY_PREFIX}${username}_${type}_${year}`;
            const cacheObj = {
                timestamp: Date.now(),
                stats: data,
                totalSubjects: totalCount
            };
            try {
                localStorage.setItem(key, JSON.stringify(cacheObj));
            } catch (e) {
                console.warn('Cache quota exceeded');
            }
        }

        // 获取用户图表显示偏好
        function getChartPrefs() {
            const defaultPrefs = { category: true, source: true, type: true, year: true };
            try {
                const saved = JSON.parse(localStorage.getItem(PREF_KEY));
                return { ...defaultPrefs, ...saved };
            } catch (e) {
                return defaultPrefs;
            }
        }

        // 保存用户偏好
        function saveChartPrefs(prefs) {
            localStorage.setItem(PREF_KEY, JSON.stringify(prefs));
        }

        // 清除所有缓存数据
        function clearAllCache() {
            if (!confirm('确定要清除所有本地缓存的数据吗？\n这将删除所有年份和类型的历史统计记录。')) {
                return;
            }
            
            const keysToRemove = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                // 匹配脚本定义的缓存前缀
                if (key && key.startsWith(CACHE_KEY_PREFIX)) {
                    keysToRemove.push(key);
                }
            }
            
            keysToRemove.forEach(k => localStorage.removeItem(k));
            
            // 界面反馈
            const status = document.getElementById('stats-status');
            if (status) status.innerText = `已清除 ${keysToRemove.length} 条缓存记录`;
            
            // 如果当前有图表，清空显示
            document.getElementById('charts-area').innerHTML = `
                <p style="width:100%; text-align:center; color:var(--bgm-text-sub); margin-top:50px;">
                    缓存已清除，请重新“开始分析”
                </p>
            `;
        }
    
        // --- 初始化 ---
    
        function init() {
            const targetUl = document.querySelector('ul.network_service.clearit');
            if (!targetUl) return; 
    
            // 1. 入口 (Li)
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="service" style="background-color:${accentColor};">TagStats</span>
                <a href="javascript:void(0);" class="l" id="bgm-stats-trigger">标签统计</a>
            `;
            targetUl.appendChild(li);
    
            // 2. 模态框 HTML
            const prefs = getChartPrefs();
            const modalHtml = `
                <div id="bgm-stats-modal">
                    <div class="bgm-stats-content">
                        <div class="bgm-loading-bar"><div class="bgm-loading-progress"></div></div>
                        <span class="bgm-stats-close">&times;</span>
                        
                        <div class="bgm-stats-top">
                            <h2 class="bgm-stats-title">标签统计分析</h2>
                            <div class="bgm-stats-controls">
                                <div class="control-group">
                                    <label>状态</label>
                                    <select id="bgm-stats-type" class="bgm-select">
                                        <option value="2" selected>看过</option>
                                        <option value="1">想看</option>
                                    </select>
                                </div>
                                <div class="control-group">
                                    <label>收藏年份</label>
                                    <select id="bgm-stats-year" class="bgm-select">
                                        <option value="all">所有年份</option>
                                    </select>
                                </div>
                                <button id="bgm-stats-load" class="action-btn">开始分析</button>
                                <button id="bgm-stats-force" class="action-btn outline-btn" title="忽略缓存，从API重新获取">更新数据</button>                              
                                <button id="bgm-stats-clear" class="action-btn text-btn" title="删除所有本地缓存记录">清除缓存</button>
                                <span id="stats-status" class="status-text">准备就绪</span>
                            </div>

                            <div class="bgm-stats-toggles">
                                <span style="font-size:12px; color:var(--bgm-text-sub); margin-right:10px;">显示图表:</span>
                                <label class="toggle-item"><input type="checkbox" data-key="category" ${prefs.category ? 'checked' : ''}> 分类</label>
                                <label class="toggle-item"><input type="checkbox" data-key="source" ${prefs.source ? 'checked' : ''}> 来源</label>
                                <label class="toggle-item"><input type="checkbox" data-key="type" ${prefs.type ? 'checked' : ''}> 类型</label>
                                <label class="toggle-item"><input type="checkbox" data-key="year" ${prefs.year ? 'checked' : ''}> 放送年份</label>
                            </div>
                        </div>
    
                        <div class="bgm-stats-body">
                            <div class="bgm-stats-charts" id="charts-area">
                                <p style="width:100%; text-align:center; color:var(--bgm-text-sub); margin-top:50px;">
                                    请选择条件并点击“开始分析”
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
    
            // 填充年份
            const yearSelect = document.getElementById('bgm-stats-year');
            const currentYear = new Date().getFullYear();
            const defaultOpt = document.createElement('option');
            defaultOpt.value = currentYear;
            defaultOpt.innerText = currentYear;
            defaultOpt.selected = true;
            yearSelect.insertBefore(defaultOpt, yearSelect.firstChild);
    
            for (let y = currentYear - 1; y >= 2008; y--) {
                const opt = document.createElement('option');
                opt.value = y;
                opt.innerText = y;
                yearSelect.appendChild(opt);
            }
    
            // 3. 事件绑定
            const triggerBtn = document.getElementById('bgm-stats-trigger');
            const modal = document.getElementById('bgm-stats-modal');
            const closeBtn = document.querySelector('.bgm-stats-close');
            const loadBtn = document.getElementById('bgm-stats-load');
            const forceBtn = document.getElementById('bgm-stats-force');
            const clearBtn = document.getElementById('bgm-stats-clear');
            const toggles = document.querySelectorAll('.bgm-stats-toggles input');
            const typeSelect = document.getElementById('bgm-stats-type');
    
            triggerBtn.addEventListener('click', () => {
                modal.style.display = 'flex';
                handleAnalysis(false);
            });
    
            closeBtn.addEventListener('click', () => modal.style.display = 'none');
            modal.addEventListener('click', (e) => {
                if (e.target.id === 'bgm-stats-modal') modal.style.display = 'none';
            });
    
            loadBtn.addEventListener('click', () => handleAnalysis(false));
            forceBtn.addEventListener('click', () => handleAnalysis(true));
            clearBtn.addEventListener('click', clearAllCache);
            
            const selects = document.querySelectorAll('#bgm-stats-year, #bgm-stats-type');
            selects.forEach(s => s.addEventListener('change', () => {
                 document.getElementById('stats-status').innerText = "条件已变更，请点击开始分析";
            }));

            typeSelect.addEventListener('change', () => {
                if (typeSelect.value === '1') { // 1 = 想看
                    yearSelect.value = 'all';
                } else {
                    yearSelect.value = currentYear;
                }
            });

            toggles.forEach(t => t.addEventListener('change', () => {
                const newPrefs = getChartPrefs();
                newPrefs[t.dataset.key] = t.checked;
                saveChartPrefs(newPrefs);

                const username = getUsername();
                const year = document.getElementById('bgm-stats-year').value;
                const type = document.getElementById('bgm-stats-type').value;

                if (username && getCache(username, type, year)) {
                     handleAnalysis(false);
                }
            }));
        }
    
        function getUsername() {
            const match = location.pathname.match(/\/user\/([^\/]+)/);
            return match ? match[1] : null;
        }
    
        async function handleAnalysis(forceRefresh) {
            const username = getUsername();
            const year = document.getElementById('bgm-stats-year').value;
            const type = document.getElementById('bgm-stats-type').value;
    
            if (!username) return alert("无法获取用户名");
    
            if (!forceRefresh) {
                const cached = getCache(username, type, year);
                if (cached) {
                    updateStatus(`已加载缓存数据 (更新于: ${new Date(cached.timestamp).toLocaleString()})`);
                    renderCharts(cached.stats, cached.totalSubjects);
                    return;
                }
            }
    
            await runAnalysis(username, type, year);
        }
    
        // --- API & 核心逻辑 ---

        function apiRequest(url) {
            return fetch(url)
            .then(response => {
                if (response.ok) {
                    return response.json();
                }
                throw new Error(`HTTP Error: ${response.status} for ${url}`);
            })
            .catch(error => {
                console.error("Fetch API Error:", error);
                throw error;
            });
        }
    
        async function fetchCollections(username, type, targetYear) {
            let allItems = [];
            let offset = 0;
            let limit = 100;
            let hasMore = true;
            
            const isYearSpecific = targetYear !== 'all';
            const targetYearInt = isYearSpecific ? parseInt(targetYear, 10) : 0;
    
            updateStatus(`正在获取列表 (${targetYear})...`);
    
            while (hasMore) {
                try {
                    const url = `${API_BASE}/users/${username}/collections?subject_type=2&type=${type}&limit=${limit}&offset=${offset}`;
                    const data = await apiRequest(url);
                    const items = data.data;
    
                    if (!items || items.length === 0) {
                        hasMore = false;
                        break;
                    }
    
                    if (isYearSpecific) {
                        for (let item of items) {
                            const dateStr = item.updated_at || item.created_at;
                            if (!dateStr) continue;
                            const itemYear = parseInt(dateStr.substring(0, 4), 10);
    
                            if (itemYear > targetYearInt) continue; 
                            if (itemYear === targetYearInt) allItems.push(item);
                            if (itemYear < targetYearInt) {
                                hasMore = false;
                                break; 
                            }
                        }
                    } else {
                        allItems = allItems.concat(items);
                    }
    
                    if (items.length < limit) hasMore = false;
                    offset += limit;
                    if (hasMore) await new Promise(r => setTimeout(r, 100));
                } catch (e) {
                    console.error("Fetch Error:", e);
                    hasMore = false;
                }
            }
            return allItems;
        }
    
        // 修改：同时返回 tags 和 date
        async function fetchSubjectData(subjectId) {
            try {
                const data = await apiRequest(`${API_BASE}/subjects/${subjectId}`);
                return {
                    tags: data.meta_tags || [],
                    date: data.date || null
                };
            } catch (e) {
                return { tags: [], date: null };
            }
        }
    
        async function runAnalysis(username, type, year) {
            const loadBtn = document.getElementById('bgm-stats-load');
            const forceBtn = document.getElementById('bgm-stats-force');
            const bar = document.querySelector('.bgm-loading-bar');
            const progress = document.querySelector('.bgm-loading-progress');
            const chartArea = document.getElementById('charts-area');
    
            loadBtn.disabled = true;
            forceBtn.disabled = true;
            bar.style.display = 'block';
            progress.style.width = '0%';
            chartArea.innerHTML = '';
            
            const collections = await fetchCollections(username, type, year);
    
            if (collections.length === 0) {
                updateStatus(`未找到符合条件的条目。`);
                loadBtn.disabled = false;
                forceBtn.disabled = false;
                bar.style.display = 'none';
                return;
            }
    
            updateStatus(`找到 ${collections.length} 条，分析中...`);
    
            let processedCount = 0;
            const subjectIds = collections.map(c => c.subject_id);
            const queue = [...subjectIds];
            const activeWorkers = [];
            
            // 初始化统计对象
            const stats = {
                category: {},
                source: {},
                type: {},
                year: {}
            };
            
            // 初始化固定字典的计数
            Object.keys(animeFilterDict).forEach(k => {
                animeFilterDict[k].forEach(tag => stats[k][tag] = 0);
            });
    
            const worker = async () => {
                while (queue.length > 0) {
                    const id = queue.shift();
                    try {
                        const data = await fetchSubjectData(id);
                        
                        // 1. 统计标签
                        data.tags.forEach(tagStr => {
                            for (let category in animeFilterDict) {
                                if (animeFilterDict[category].includes(tagStr)) {
                                    stats[category][tagStr]++;
                                }
                            }
                        });

                        // 2. 统计年份
                        if (data.date) {
                            // 提取 "2000-04-18" -> "2000"
                            const yStr = data.date.substring(0, 4);
                            if (/^\d{4}$/.test(yStr)) {
                                if (!stats.year[yStr]) stats.year[yStr] = 0;
                                stats.year[yStr]++;
                            }
                        }

                    } catch (e) { /* ignore */ }
                    
                    processedCount++;
                    const pct = Math.round((processedCount / subjectIds.length) * 100);
                    progress.style.width = `${pct}%`;
                    updateStatus(`分析进度: ${processedCount}/${subjectIds.length}`);
                    
                    await new Promise(r => setTimeout(r, RETRY_DELAY));
                }
            };
    
            for (let i = 0; i < CONCURRENCY_LIMIT; i++) activeWorkers.push(worker());
            await Promise.all(activeWorkers);
    
            setCache(username, type, year, stats, collections.length);
            
            updateStatus(`统计完成 (共${collections.length}条)，已缓存`);
            renderCharts(stats, collections.length);
            
            loadBtn.disabled = false;
            forceBtn.disabled = false;
            bar.style.display = 'none';
        }
    
        function updateStatus(msg) {
            const el = document.getElementById('stats-status');
            if(el) el.innerText = msg;
        }
    
        // --- 图表绘制 ---
    
        function renderCharts(stats, totalSubjects) {
            const container = document.getElementById('charts-area');
            container.innerHTML = ''; 
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const prefs = getChartPrefs(); 
            
            const baseColors = [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40',
                '#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4',
                '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990', '#dcbeff'
            ];
            const otherColor = isDark ? '#666666' : '#cccccc';
            const textColor = isDark ? '#eeeeee' : '#333333';

            Chart.defaults.color = textColor;
            Chart.defaults.borderColor = isDark ? '#444' : '#fff';
            Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

            let hasData = false;

            for (let key in stats) {
                if (prefs[key] === false) continue;

                const rawData = stats[key];
                let totalTags = Object.values(rawData).reduce((a, b) => a + b, 0);
                
                if (totalTags === 0) continue;
                hasData = true;

                const sorted = Object.entries(rawData).sort((a, b) => b[1] - a[1]);
                
                let visibleItems = [];
                let otherCandidates = [];

                sorted.forEach((entry, index) => {
                    const count = entry[1];
                    if (count === 0) return;
                    
                    const percentage = count / totalTags;
                    const color = baseColors[index % baseColors.length];

                    if (percentage >= MIN_PERCENTAGE) {
                        visibleItems.push({ label: entry[0], count: count, color: color });
                    } else {
                        otherCandidates.push({ label: entry[0], count: count, color: color });
                    }
                });

                // 判断“其他”里有几个
                if (otherCandidates.length === 1) {
                    // 只有1个，不合并，直接显示原数据
                    visibleItems.push(otherCandidates[0]);
                    otherCandidates = [];
                } else if (otherCandidates.length > 1) {
                    // 大于1个，才合并
                    const totalOther = otherCandidates.reduce((sum, item) => sum + item.count, 0);
                    visibleItems.push({ label: '其他', count: totalOther, color: otherColor });
                }

                // 生成最终数组
                const labels = visibleItems.map(i => i.label);
                const dataPoints = visibleItems.map(i => i.count);
                const colors = visibleItems.map(i => i.color);

                const wrapper = document.createElement('div');
                wrapper.className = 'chart-container';
                const canvas = document.createElement('canvas');
                wrapper.appendChild(canvas);
                container.appendChild(wrapper);

                new Chart(canvas, {
                    type: 'pie',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: dataPoints,
                            backgroundColor: colors,
                            borderWidth: 2,
                            borderColor: isDark ? '#38393b' : '#fafafa'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom', labels: { boxWidth: 12, padding: 20, usePointStyle: true } },
                            title: { display: true, text: titleMap[key] || key, font: { size: 16, weight: '600' }, padding: { bottom: 20 } },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        let val = context.raw;
                                        let pct = ((val / totalTags) * 100).toFixed(1) + '%';
                                        return ` ${context.label}: ${val} (${pct})`;
                                    }
                                }
                            }
                        }
                    }
                });
                canvas.style.height = '280px';
            }

            if (!hasData) {
                container.innerHTML = `<p style="width:100%; text-align:center; color:var(--bgm-text-sub); margin-top:50px;">当前条件无标签数据</p>`;
            }
        }
    
        init();
    }
    
    loadChartJS(mainAppLogic);

})();



// /* --- CSS Styles for Bangumi Stats Script --- */

// :root {
//     --bgm-bg-modal: rgba(0,0,0,0.6);
//     --bgm-bg-content: #ffffff;
//     --bgm-text-main: #333333;
//     --bgm-text-sub: #888888;
//     --bgm-border: #eeeeee;
//     --bgm-card-bg: #fafafa;
// }

// /* 深色模式覆盖 */
// html[data-theme="dark"] {
//     --bgm-bg-content: #2d2e2f;
//     --bgm-text-main: #eeeeee;
//     --bgm-text-sub: #aaaaaa;
//     --bgm-border: #444444;
//     --bgm-card-bg: #38393b;
// }

// /* 模态框 */
// #bgm-stats-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: var(--bgm-bg-modal); z-index: 10000; justify-content: center; align-items: center; backdrop-filter: blur(3px); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }
// .bgm-stats-content { background: var(--bgm-bg-content); width: 90%; max-width: 1100px; padding: 0; border-radius: 12px; max-height: 90vh; overflow-y: auto; position: relative; box-shadow: 0 15px 40px rgba(0,0,0,0.3); display: flex; flex-direction: column; }

// /* 头部区域 */
// .bgm-stats-top { padding: 25px 30px 15px 30px; border-bottom: 1px solid var(--bgm-border); }
// .bgm-stats-title { margin: 0 0 15px 0; font-size: 22px; color: var(--bgm-text-main); font-weight: 600; }

// /* 控件栏 */
// .bgm-stats-controls { display: flex; gap: 20px; align-items: center; flex-wrap: wrap; margin-bottom: 15px; }
// .control-group { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--bgm-text-main); }

// /* 显示开关栏*/
// .bgm-stats-toggles { display: flex; align-items: center; gap: 15px; flex-wrap: wrap; padding-top: 5px; }
// .toggle-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--bgm-text-main); cursor: pointer; user-select: none; }
// .toggle-item input[type="checkbox"] { cursor: pointer; accent-color: var(--bgm-accent); width: 15px; height: 15px; }

// .bgm-stats-close { position: absolute; top: 20px; right: 25px; cursor: pointer; font-size: 28px; color: var(--bgm-text-sub); transition: color 0.2s; line-height: 1; }
// .bgm-stats-close:hover { color: var(--bgm-accent); }

// /* 图表容器 */
// .bgm-stats-body { padding: 30px; overflow-y: auto; }
// .bgm-stats-charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 25px; }
// .chart-container { border: 1px solid var(--bgm-border); padding: 20px; border-radius: 10px; text-align: center; background: var(--bgm-card-bg); transition: transform 0.2s; }
// .chart-container:hover { border-color: var(--bgm-accent); }

// /* 进度条 */
// .bgm-loading-bar { width: 100%; height: 4px; background: var(--bgm-border); display: none; position: absolute; top: 0; left: 0; }
// .bgm-loading-progress { width: 0%; height: 100%; background: var(--bgm-accent); transition: width 0.2s ease; box-shadow: 0 0 10px var(--bgm-accent); }

// /* 按钮与输入框 */
// select.bgm-select { padding: 6px 12px; border: 1px solid var(--bgm-border); border-radius: 6px; font-size: 14px; background: var(--bgm-bg-content); color: var(--bgm-text-main); outline: none; }
// select.bgm-select:focus { border-color: var(--bgm-accent); }

// button.action-btn { background: var(--bgm-accent); color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500; transition: filter 0.2s; display: flex; align-items: center; gap: 5px; }
// button.action-btn:hover { filter: brightness(1.1); }
// button.action-btn:disabled { background: #cccccc; cursor: not-allowed; filter: none; }
// button.outline-btn { background: transparent; border: 1px solid var(--bgm-accent); color: var(--bgm-accent); }
// button.outline-btn:hover { background: var(--bgm-accent); color: white; }
// button.text-btn { background: transparent; border: 1px dashed var(--bgm-border); color: var(--bgm-text-sub); transition: all 0.2s; }
// button.text-btn:hover { border-color: var(--bgm-accent); color: var(--bgm-accent); background: transparent;filter: none; }

// .status-text { margin-left: auto; color: var(--bgm-text-sub); font-size: 13px; font-style: italic; }

// /* === 修复 network_service 换行对齐问题 === */
// ul.network_service { display: flex; flex-wrap: wrap; justify-content: flex-start; }