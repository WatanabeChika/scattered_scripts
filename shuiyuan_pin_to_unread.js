// ==UserScript==
// @name         水源未读页话题常驻置顶 (Shuiyuan Pin to Unread)
// @namespace    https://shuiyuan.sjtu.edu.cn/
// @version      1.0.2
// @description  将想跟进的帖子固定在水源未读页面（/unread）顶部，自适应所有主题并支持实时显示未读条数与标题表情
// @author       Collaborator
// @match        https://shuiyuan.sjtu.edu.cn/*
// @grant        none
// @license      MIT
// ==/UserScript==

(() => {
    'use strict';

    const pageWindow = typeof unsafeWindow !== 'undefined' ? unsafeWindow : window;
    if (pageWindow.shuiyuanPinUnreadLoaded) {
        return;
    }
    pageWindow.shuiyuanPinUnreadLoaded = true;

    const STORAGE_KEY = 'shuiyuan_pinned_unread_topics_v1';
    const FETCH_CONCURRENCY = 3;
    const REFRESH_COOLDOWN_MS = 15000; // 15秒内不重复请求同一话题JSON

    const IS_MOBILE_VIEW = () => document.documentElement.classList.contains('mobile-view');
    const IS_MOBILE_DEVICE = () => document.documentElement.classList.contains('mobile-device');

    // Font Awesome 图钉图标 (显式声明宽高属性以兼容 Firefox / Safari)
    const THUMBTACK_ICON = '<svg class="fa d-icon d-icon-thumbtack svg-icon prefix-icon svg-string" width="12" height="12" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512"><path d="M32 32C32 14.3 46.3 0 64 0H320c17.7 0 32 14.3 32 32s-14.3 32-32 32H290.5l11.4 148.2c36.7 19.9 65.7 53.2 79.5 94.7l1 3c3.3 9.8 1.6 20.5-4.4 28.8s-15.7 13.3-26 13.3H32c-10.3 0-19.9-4.9-26-13.3s-7.7-19.1-4.4-28.8l1-3c13.8-41.5 42.8-74.8 79.5-94.7L93.5 64H64C46.3 64 32 49.7 32 32zM160 384h64v96c0 17.7-14.3 32-32 32s-32-14.3-32-32V384z"/></svg>';

    // 内存缓存与防重入锁
    const lastRefreshTimeMap = new Map();
    let isRefreshing = false;
    let pendingForcedRefresh = false;
    let isMutatingDOM = false;
    let isRouteTransitioning = false;
    let pageObserver = null;
    const observerOptions = { childList: true, subtree: true, characterData: true };

    // MutationObserver 异步派发，仅用布尔锁无法过滤脚本自己的 DOM 变化。
    const mutateDOM = (callback) => {
        if (isMutatingDOM) return callback();
        pageObserver?.disconnect();
        isMutatingDOM = true;
        try {
            return callback();
        } finally {
            isMutatingDOM = false;
            pageObserver?.observe(document.documentElement, observerOptions);
        }
    };

    const getDiscourseContainer = () => {
        try {
            return pageWindow.Discourse?.__container__
                || pageWindow.require?.('discourse/lib/url')?.default?.container;
        } catch {
            return null;
        }
    };

    const getDiscourseRouter = () => getDiscourseContainer()?.lookup?.('service:router');

    const isPageTransitioning = () => {
        if (isRouteTransitioning) return true;
        const router = getDiscourseRouter();
        if (router?.activeTransition) return true;
        // popstate 先改地址，Ember 随后才切换页面；保留正在离开的列表直到切换完成。
        const routePath = router?.currentURL?.split(/[?#]/)[0];
        return Boolean(routePath && routePath !== window.location.pathname);
    };

    // ==================== 站点配置、主题与表情字典 ====================
    let dataPreloadedCache = null;
    const getDataPreloaded = () => {
        if (dataPreloadedCache) return dataPreloadedCache;
        try {
            const el = document.getElementById('data-preloaded');
            if (el) {
                dataPreloadedCache = JSON.parse(el.getAttribute('data-preloaded') || '{}');
            }
        } catch (e) {
            console.error('[水源未读常驻] 解析 data-preloaded 失败:', e);
        }
        return dataPreloadedCache || {};
    };

    const getSiteSettings = () => {
        try {
            const liveSettings = getDiscourseContainer()?.lookup?.('service:site-settings');
            if (liveSettings) return liveSettings;
            const raw = getDataPreloaded().siteSettings;
            if (raw) return JSON.parse(raw);
        } catch {
            // ignore
        }
        return {};
    };

    let customEmojisMapCache = null;
    const getCustomEmojisMap = () => {
        if (customEmojisMapCache) return customEmojisMapCache;
        customEmojisMapCache = new Map();
        try {
            const raw = getDataPreloaded().customEmoji;
            if (raw) {
                const list = JSON.parse(raw);
                for (const item of list || []) {
                    if (item?.name && item?.url) {
                        customEmojisMapCache.set(item.name, item.url);
                    }
                }
            }
        } catch (e) {
            console.error('[水源未读常驻] 解析 customEmoji 失败:', e);
        }
        return customEmojisMapCache;
    };

    const getEmojiUrl = (emojiName) => {
        const customMap = getCustomEmojisMap();
        if (customMap.has(emojiName)) {
            return customMap.get(emojiName);
        }
        try {
            const textLib = pageWindow.require?.('discourse/lib/text');
            if (textLib?.emojiUrlFor) {
                const url = textLib.emojiUrlFor(emojiName);
                if (url) return url;
            }
        } catch {
            // fallback below
        }
        const emojiSet = getSiteSettings().emoji_set || 'google';
        return `/images/emoji/${encodeURIComponent(emojiSet)}/${encodeURIComponent(emojiName).replaceAll('%3A', '/')}.png`;
    };

    const escapeHTML = (str) => String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    // 将标题文本（含 :shortcode: 或 fancy_title）安全渲染到目标 DOM 元素中
    const setTitleElementWithEmojis = (targetEl, record) => {
        const baseHTML = record.fancy_title || escapeHTML(record.title || `话题 #${record.id}`);
        let processedHTML = baseHTML;

        // 1. 优先通过 Discourse 内置 emojiUnescape 处理标准表情与自定义表情
        try {
            const textLib = pageWindow.require?.('discourse/lib/text');
            const prettyEmoji = pageWindow.require?.('pretty-text/emoji');
            const unescapeFn = textLib?.emojiUnescape || prettyEmoji?.emojiUnescape;
            if (typeof unescapeFn === 'function') {
                processedHTML = unescapeFn(processedHTML);
            }
        } catch {
            // fallback below
        }

        targetEl.innerHTML = processedHTML;

        // 2. 兜底处理：针对紧贴中文无空格等情况遗留的 :shortcode: 文本节点进行转换
        const walker = document.createTreeWalker(targetEl, NodeFilter.SHOW_TEXT, null);
        const textNodesToReplace = [];
        let currentNode = walker.nextNode();
        while (currentNode) {
            if (/:[a-zA-Z0-9_+-]+:/.test(currentNode.nodeValue)) {
                textNodesToReplace.push(currentNode);
            }
            currentNode = walker.nextNode();
        }

        for (const textNode of textNodesToReplace) {
            const text = textNode.nodeValue;
            const regex = /:([a-zA-Z0-9_+-]+):/g;
            let lastIndex = 0;
            let match;
            const frag = document.createDocumentFragment();

            while ((match = regex.exec(text)) !== null) {
                if (match.index > lastIndex) {
                    frag.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
                }
                const fullCode = match[0];
                const emojiName = match[1];
                const url = getEmojiUrl(emojiName);

                const img = document.createElement('img');
                img.width = 20;
                img.height = 20;
                img.src = url;
                img.title = fullCode;
                img.alt = fullCode;
                img.className = 'emoji';
                // 若并非真实表情（图片404），自动回退为原始 :xxx: 文本
                img.addEventListener('error', () => {
                    img.replaceWith(document.createTextNode(fullCode));
                }, { once: true });

                frag.appendChild(img);
                lastIndex = regex.lastIndex;
            }
            if (lastIndex < text.length) {
                frag.appendChild(document.createTextNode(text.slice(lastIndex)));
            }
            textNode.replaceWith(frag);
        }
    };

    // 从页面已有标题 DOM 中提取含 :shortcode: 的完整标题文本
    const extractTitleFromDOM = () => {
        const titleEl = document.querySelector('#topic-title h1 a.fancy-title, #topic-title h1 a, .d-header .header-title .topic-link');
        if (!titleEl) return '';
        const clone = titleEl.cloneNode(true);
        for (const btn of clone.querySelectorAll('.shuiyuan-pin-btn')) {
            btn.remove();
        }
        for (const img of clone.querySelectorAll('img.emoji')) {
            const altText = img.getAttribute('alt') || img.getAttribute('title') || '';
            img.replaceWith(document.createTextNode(altText));
        }
        return clone.textContent?.trim() || '';
    };

    const getCurrentThemeId = () => {
        const themeMeta = document.querySelector('meta[name="discourse_theme_id"]');
        const id = parseInt(themeMeta?.content, 10);
        return Number.isNaN(id) ? null : id;
    };

    // ==================== 样式注入（兼容全主题与深浅色模式） ====================
    const addGlobalStyle = (css) => {
        const style = document.createElement('style');
        style.appendChild(document.createTextNode(css));
        document.head.appendChild(style);
        return style;
    };

    addGlobalStyle(`
        /* 话题内标题栏与首行冻结栏中的置顶按钮 */
        .shuiyuan-pin-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            margin-left: 10px;
            padding: 3px 9px;
            font-size: 13px;
            font-weight: normal;
            line-height: 1.35;
            color: var(--primary-medium, #888);
            background: transparent;
            border: 1px solid var(--primary-low-mid, #666);
            border-radius: var(--d-button-border-radius, 4px);
            cursor: pointer;
            vertical-align: middle;
            transition: color 0.18s ease, background-color 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
            user-select: none;
            flex-shrink: 0;
            white-space: nowrap;
            box-sizing: border-box;
            -webkit-appearance: button;
        }
        .shuiyuan-pin-btn > svg {
            width: 12px !important;
            height: 12px !important;
            fill: currentColor;
            flex-shrink: 0;
            transition: transform 0.18s ease;
        }
        .shuiyuan-pin-btn.is-pinned {
            color: var(--tertiary, #0088cc);
            border-color: var(--tertiary, #0088cc);
            background: var(--tertiary-low, rgba(0, 136, 204, 0.15));
            font-weight: 500;
        }
        .shuiyuan-pin-btn.is-pinned > svg {
            transform: rotate(-35deg);
        }
        /* 首行冻结栏弹性布局保护，防止长标题将按钮挤出屏幕 */
        .d-header .extra-info-wrapper .header-title {
            display: flex;
            align-items: center;
            min-width: 0;
        }
        .d-header .extra-info-wrapper .header-title > a,
        .d-header .extra-info-wrapper .header-title .topic-link {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            min-width: 0;
        }
        .d-header .extra-info-wrapper .shuiyuan-pin-btn {
            padding: 2px 8px;
            font-size: 12px;
            margin-left: 8px;
        }

        /* 未读页面常驻话题的图钉按钮与标题内 Emoji 尺寸对齐 */
        .shuiyuan-pin-row .topic-status.shuiyuan-unpin-trigger {
            cursor: pointer;
            color: var(--tertiary, #0088cc);
            margin-right: 5px;
            display: inline-flex;
            align-items: center;
            vertical-align: middle;
            transition: color 0.15s ease, transform 0.15s ease;
        }
        .shuiyuan-pin-row .topic-status.shuiyuan-unpin-trigger > svg {
            width: 14px !important;
            height: 14px !important;
            fill: currentColor;
            transform: rotate(-35deg);
        }
        .shuiyuan-pin-row a.title img.emoji {
            width: 20px;
            height: 20px;
            vertical-align: middle;
        }

        /* 常驻话题与普通未读话题之间的分隔线 */
        tr.topic-list-item-separator.shuiyuan-pin-separator td.topic-list-data {
            border-bottom: 1px solid var(--primary-low-mid, rgba(136, 136, 136, 0.35));
            padding: 0 !important;
            height: 1px !important;
            line-height: 0 !important;
        }

        /* 隐藏原生列表中与已常驻话题重复的行 */
        tr.topic-list-item.shuiyuan-pin-hidden-native {
            display: none !important;
        }
    `);

    if (!IS_MOBILE_DEVICE()) {
        addGlobalStyle(`
            .shuiyuan-pin-btn:hover {
                color: var(--tertiary, #0088cc);
                border-color: var(--tertiary, #0088cc);
                background: var(--tertiary-very-low, rgba(0, 136, 204, 0.08));
            }
            .shuiyuan-pin-btn.is-pinned:hover {
                color: var(--danger, #e45735);
                border-color: var(--danger, #e45735);
                background: var(--danger-low, rgba(228, 87, 53, 0.12));
            }
            .shuiyuan-pin-row .topic-status.shuiyuan-unpin-trigger:hover {
                color: var(--danger, #e45735);
                transform: scale(1.15);
            }
        `);
    }

    // 针对特定主题（如 Isabelle 主题）适配圆角风格
    if (getCurrentThemeId() === 43) {
        addGlobalStyle(`
            .shuiyuan-pin-btn {
                border-radius: 16px;
            }
        `);
    }

    // ==================== 存储与数据工具 ====================
    const normalizeTagItem = (tag) => {
        if (!tag) return null;
        if (typeof tag === 'string') {
            if (tag === '[object Object]') return null;
            return { name: tag, slug: tag };
        }
        if (typeof tag === 'object') {
            const name = tag.name ?? tag.text ?? tag.slug ?? tag.id;
            const slug = tag.slug ?? name;
            if (name !== undefined && name !== null && String(name) !== '[object Object]') {
                return { name: String(name), slug: String(slug) };
            }
        }
        return null;
    };

    const normalizeTagsArray = (tags) => {
        if (!Array.isArray(tags)) return [];
        return tags.map(normalizeTagItem).filter(Boolean);
    };

    const loadPinnedMap = () => {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return new Map();
            const arr = JSON.parse(raw);
            if (!Array.isArray(arr)) return new Map();
            const map = new Map();
            for (const item of arr) {
                if (item && Number.isInteger(item.id) && item.id > 0) {
                    item.tags = normalizeTagsArray(item.tags);
                    map.set(item.id, item);
                }
            }
            return map;
        } catch (e) {
            console.error('[水源未读常驻] 读取存储失败:', e);
            return new Map();
        }
    };

    const savePinnedMap = (map) => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify([...map.values()]));
        } catch (e) {
            console.error('[水源未读常驻] 保存存储失败:', e);
        }
    };

    const isTopicPinned = (topicId) => loadPinnedMap().has(Number(topicId));

    // 获取预加载的站点分类字典（完整保留 parent_category_id 与 Ember 模型引用）
    let categoriesMapCache = null;
    const getCategoriesMap = () => {
        if (categoriesMapCache && categoriesMapCache.size > 0) return categoriesMapCache;
        categoriesMapCache = new Map();
        try {
            const preloaded = getDataPreloaded();
            if (preloaded.site) {
                const site = JSON.parse(preloaded.site || '{}');
                for (const c of site.categories || []) {
                    categoriesMapCache.set(Number(c.id), { ...c, id: Number(c.id) });
                }
            }
            const siteService = getDiscourseContainer()?.lookup?.('service:site');
            if (siteService?.categories) {
                for (const c of siteService.categories) {
                    const id = Number(c.id);
                    const existing = categoriesMapCache.get(id) || {};
                    categoriesMapCache.set(id, {
                        ...existing,
                        id,
                        name: c.name ?? existing.name,
                        slug: c.slug ?? existing.slug,
                        color: c.color ?? existing.color,
                        text_color: c.text_color ?? existing.text_color,
                        style_type: c.style_type ?? existing.style_type,
                        parent_category_id: c.parent_category_id ?? c.parentCategory?.id ?? existing.parent_category_id ?? null,
                        _emberModel: c,
                    });
                }
            }
        } catch (e) {
            console.error('[水源未读常驻] 解析分类信息失败:', e);
        }
        return categoriesMapCache;
    };

    // Discourse 站内无刷新跳转（兼容 Ctrl/Shift/Cmd/中键新标签页打开）
    const navigateTo = (e, path) => {
        if (!path || e.ctrlKey || e.shiftKey || e.metaKey || e.altKey || (e.button !== undefined && e.button !== 0)) {
            return;
        }
        e.preventDefault();
        e.stopPropagation();
        try {
            const DiscourseURL = pageWindow.require?.('discourse/lib/url')?.default;
            if (DiscourseURL?.routeTo) {
                DiscourseURL.routeTo(path);
                return;
            }
        } catch {
            // fallback below
        }
        // 路由模块不可用时使用普通跳转，不通过 back/forward 人为触发路由。
        window.location.assign(path);
    };

    // 请求封装
    const discourseFetchJSON = async (url) => {
        const csrf = document.querySelector('meta[name="csrf-token"]')?.content ?? '';
        const res = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Discourse-Present': 'true',
                'Discourse-Logged-In': 'true',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': csrf,
            },
            mode: 'same-origin',
            credentials: 'include',
        });
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
    };

    // 数字与相对时间格式化（与水源原生保持一致）
    const formatCount = (num) => {
        if (!Number.isFinite(num) || num < 0) return '0';
        try {
            const formatter = pageWindow.require?.('discourse/lib/formatter');
            if (formatter?.number) {
                return formatter.number(num);
            }
        } catch {
            // fallback below
        }
        if (num < 1000) return String(num);
        if (num < 10000) return `${(num / 1000).toFixed(1)}k`;
        if (num < 1000000) return `${Math.round(num / 1000)}k`;
        return `${(num / 1000000).toFixed(1)}M`;
    };

    const formatRelativeTime = (isoString) => {
        if (!isoString) return '';
        const date = new Date(isoString);
        if (Number.isNaN(date.getTime())) return '';
        const diffMs = Date.now() - date.getTime();
        const min = diffMs / 60000;
        const hour = min / 60;
        const day = hour / 24;
        if (min < 1) return '1 分钟';
        if (min < 59.5) return `${Math.round(min)} 分钟`;
        if (hour < 23.5) return `${Math.round(hour)} 小时`;
        if (day < 30) return `${Math.max(1, Math.round(day))} 天`;
        const now = new Date();
        if (date.getFullYear() === now.getFullYear()) {
            return `${date.getMonth() + 1} 月 ${date.getDate()} 日`;
        }
        return `${String(date.getFullYear()).slice(-2)} 年 ${date.getMonth() + 1} 月`;
    };

    // 根据数值返回 Discourse 原生热度样式类 (heatmap-low / med / high)
    const getPostsHeatmapClass = (replies) => {
        if (replies >= 500) return 'heatmap-high';
        if (replies >= 100) return 'heatmap-med';
        if (replies >= 30) return 'heatmap-low';
        return '';
    };

    const getViewsHeatmapClass = (views) => {
        if (views >= 3500) return 'heatmap-high';
        if (views >= 1000) return 'heatmap-med';
        if (views >= 300) return 'heatmap-low';
        return '';
    };

    // ==================== 解析与更新话题详情 ====================
    const extractPostersFromTopicJSON = (data) => {
        const posters = [];
        const seenIds = new Set();
        const createdBy = data.details?.created_by;
        const lastPoster = data.details?.last_poster;
        const participants = data.details?.participants || [];

        const addPoster = (user, isLatest = false, isOriginal = false) => {
            if (!user || !user.username) return;
            const uid = user.id ?? user.username;
            if (seenIds.has(uid)) return;
            seenIds.add(uid);
            posters.push({
                id: user.id,
                username: user.username,
                name: user.name || user.username,
                avatar_template: user.avatar_template || '/images/avatar.png',
                isLatest,
                isOriginal,
            });
        };

        if (createdBy) {
            const sameAsLast = lastPoster && lastPoster.username === createdBy.username;
            addPoster(createdBy, sameAsLast, true);
        }
        for (const p of participants) {
            if (posters.length >= 4 && lastPoster && !seenIds.has(lastPoster.id ?? lastPoster.username)) {
                break;
            }
            if (posters.length >= 5) break;
            if (lastPoster && p.username === lastPoster.username) continue;
            addPoster(p, false, false);
        }
        if (lastPoster && posters.length < 5) {
            addPoster(lastPoster, true, false);
        }
        return posters;
    };

    const parseTopicJSONToRecord = (data, existingRecord = {}) => {
        const highestPost = data.highest_post_number ?? existingRecord.highest_post_number ?? 1;
        const lastReadPost = data.last_read_post_number ?? existingRecord.last_read_post_number ?? highestPost;
        const unreadPosts = Math.max(0, highestPost - lastReadPost);
        const postsCount = data.posts_count ?? existingRecord.posts_count ?? 1;
        const extractedPosters = extractPostersFromTopicJSON(data);

        return {
            id: Number(data.id),
            title: data.title || existingRecord.title || `话题 #${data.id}`,
            fancy_title: data.fancy_title || existingRecord.fancy_title || '',
             unicode_title: data.unicode_title || existingRecord.unicode_title || '',
            slug: data.slug || existingRecord.slug || 'topic',
            category_id: data.category_id ?? existingRecord.category_id ?? null,
            tags: Array.isArray(data.tags)
                ? normalizeTagsArray(data.tags)
                : normalizeTagsArray(existingRecord.tags),
            posts_count: postsCount,
            reply_count: Math.max(0, postsCount - 1),
            views: data.views ?? existingRecord.views ?? 0,
            last_posted_at: data.last_posted_at || data.bumped_at || data.created_at || existingRecord.last_posted_at || new Date().toISOString(),
            created_at: data.created_at || existingRecord.created_at || '',
            highest_post_number: highestPost,
            last_read_post_number: lastReadPost,
            unread_posts: unreadPosts,
            posters: extractedPosters.length > 0 ? extractedPosters : (existingRecord.posters || []),
            pinned_at: existingRecord.pinned_at || Date.now(),
        };
    };

    // 仅在实际浏览该话题时同步已读进度。列表跟踪器会补偿性地把缺失话题标为已读，
    // 不能在渲染未读列表时用它覆盖话题 JSON 的真实已读进度。
    const syncWithTrackingState = (record) => {
        if (getCurrentTopicIdInView() !== record.id) return record;
        try {
            const container = getDiscourseContainer();
            const trackingState = container?.lookup?.('service:topic-tracking-state')
                || container?.lookup?.('topic-tracking-state:main');
            const state = trackingState?.findState?.(record.id)
                || trackingState?.states?.get?.(`t${record.id}`)
                || trackingState?.states?.[`t${record.id}`];
            if (state) {
                if (Number.isInteger(state.highest_post_number)) {
                    record.highest_post_number = Math.max(record.highest_post_number || 1, state.highest_post_number);
                }
                if (Number.isInteger(state.last_read_post_number)) {
                    record.last_read_post_number = state.last_read_post_number;
                }
                if (Number.isInteger(record.highest_post_number) && Number.isInteger(record.last_read_post_number)) {
                    record.unread_posts = Math.max(0, record.highest_post_number - record.last_read_post_number);
                }
            }
        } catch {
            // ignore
        }
        return record;
    };

    // ==================== 当前页面状态判断 ====================
    const isUnreadPage = () => {
        const path = window.location.pathname.toLowerCase();
        if (path === '/unread' || path.startsWith('/unread/')) {
            return true;
        }
        // 兼容将“未读”设为水源默认首页（打开 https://shuiyuan.sjtu.edu.cn/ 直接是未读页）的情况
        if (path === '/' || path === '') {
            const activeUnreadNav = document.querySelector(
                '#navigation-bar li.nav-item_unread.active, #navigation-bar a[href$="/unread"].active, .navigation-container .nav-pills a[href$="/unread"].active'
            );
            if (activeUnreadNav) {
                return true;
            }
            try {
                const router = getDiscourseRouter();
                if (router?.currentRouteName?.startsWith('discovery.unread')) {
                    return true;
                }
            } catch {
                // ignore
            }
        }
        return false;
    };

    const getCurrentTopicIdInView = () => {
        // 后退时 URL 已变，但旧话题 DOM 可能仍在，不能从旧 DOM 判断当前话题。
        const match = window.location.pathname.match(/^\/t\/(\d+)(?:\/|$)/)
            || window.location.pathname.match(/^\/t\/[^/]+\/(\d+)(?:\/|$)/);
        if (match) {
            return parseInt(match[1], 10);
        }
        return null;
    };

    // ==================== 置顶 / 移出核心操作 ====================
    const togglePinTopic = async (topicId, fallbackTitle = '') => {
        const numericId = Number(topicId);
        if (!Number.isInteger(numericId) || numericId <= 0) return;

        const map = loadPinnedMap();
        if (map.has(numericId)) {
            map.delete(numericId);
            savePinnedMap(map);
            updateAllPinButtonsState();
            if (isUnreadPage()) {
                renderPinnedTopicsOnUnreadPage();
            }
            return false;
        }

        // 先构造初始记录立即保存（保留标题中的表情短代码），保证按钮瞬时响应
        const domTitle = fallbackTitle || extractTitleFromDOM() || `话题 #${numericId}`;
        const initialRecord = {
            id: numericId,
            title: domTitle,
            fancy_title: escapeHTML(domTitle),
            slug: 'topic',
            category_id: null,
            tags: [],
            posts_count: 1,
            reply_count: 0,
            views: 0,
            last_posted_at: new Date().toISOString(),
            highest_post_number: 1,
            last_read_post_number: 1,
            unread_posts: 0,
            posters: [],
            pinned_at: Date.now(),
        };
        map.set(numericId, initialRecord);
        savePinnedMap(map);
        updateAllPinButtonsState();

        // 异步拉取完整话题信息以填充父子分类、标签、头像、楼层数
        try {
            const data = await discourseFetchJSON(`/t/${numericId}.json?track_visit=false`);
            const updatedMap = loadPinnedMap();
            if (updatedMap.has(numericId)) {
                const fullRecord = parseTopicJSONToRecord(data, initialRecord);
                updatedMap.set(numericId, fullRecord);
                savePinnedMap(updatedMap);
                lastRefreshTimeMap.set(numericId, Date.now());
                if (isUnreadPage()) {
                    renderPinnedTopicsOnUnreadPage();
                }
            }
        } catch (e) {
            console.error('[水源未读常驻] 获取话题详情失败:', e);
        }
        return true;
    };

    // ==================== 话题内标题栏 & 首行冻结栏按钮 ====================
    const createPinButtonElement = (topicId) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'shuiyuan-pin-btn';
        btn.setAttribute('data-topic-id', String(topicId));

        const updateBtnAppearance = (hovering = false) => {
            const pinned = isTopicPinned(topicId);
            btn.classList.toggle('is-pinned', pinned);
            const labelText = pinned ? (hovering ? '移出' : '已置顶') : '置顶';
            btn.title = pinned
                ? '从「未读」页顶部移出该话题'
                : '固定到「未读」页顶部，方便随时追更';
            btn.innerHTML = `${THUMBTACK_ICON}<span class="shuiyuan-pin-btn-text">${labelText}</span>`;
        };

        updateBtnAppearance(false);
        btn.addEventListener('mouseenter', () => updateBtnAppearance(true));
        btn.addEventListener('mouseleave', () => updateBtnAppearance(false));
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            await togglePinTopic(topicId);
            updateBtnAppearance(false);
        });

        btn._updateAppearance = () => updateBtnAppearance(false);
        return btn;
    };

    const updateAllPinButtonsState = () => {
        const currentTopicId = getCurrentTopicIdInView();
        for (const btn of document.querySelectorAll('.shuiyuan-pin-btn')) {
            if (currentTopicId) {
                btn.setAttribute('data-topic-id', String(currentTopicId));
            }
            btn._updateAppearance?.();
        }
    };

    const injectTopicHeaderPinButtons = () => {
        const topicId = getCurrentTopicIdInView();
        if (!topicId) return;

        // 1. 顶部主标题栏 (#topic-title .title-wrapper h1)
        const mainTitleH1 = document.querySelector('#topic-title .title-wrapper h1, #topic-title h1');
        if (mainTitleH1) {
            const existingBtn = mainTitleH1.querySelector('.shuiyuan-pin-btn');
            if (!existingBtn) {
                mainTitleH1.appendChild(createPinButtonElement(topicId));
            } else if (existingBtn.getAttribute('data-topic-id') !== String(topicId)) {
                existingBtn.replaceWith(createPinButtonElement(topicId));
            }
        }

        // 2. 向下滚动后首行冻结的顶部标题栏 (.d-header .extra-info-wrapper .header-title)
        const stickyHeaderTitle = document.querySelector('.d-header .extra-info-wrapper .header-title, .d-header .header-title');
        if (stickyHeaderTitle) {
            const existingStickyBtn = stickyHeaderTitle.querySelector('.shuiyuan-pin-btn');
            if (!existingStickyBtn) {
                stickyHeaderTitle.appendChild(createPinButtonElement(topicId));
            } else if (existingStickyBtn.getAttribute('data-topic-id') !== String(topicId)) {
                existingStickyBtn.replaceWith(createPinButtonElement(topicId));
            }
        }

        // 当用户正在浏览已常驻的话题时，顺便同步已读进度
        const map = loadPinnedMap();
        if (map.has(topicId)) {
            const rec = syncWithTrackingState(map.get(topicId));
            map.set(topicId, rec);
            savePinnedMap(map);
        }
    };

    // ==================== 未读页面渲染常驻话题列表 ====================
    // 构建单个分类徽标节点（供父分类和子分类分别调用）
    const buildSingleCategoryBadge = (cat, parentCat = null) => {
        // 优先使用 Discourse 原生 categoryBadgeHTML helper，传入 hideParent: true 以独立渲染每个层级的分类块
        try {
            const categoryLinkHelper = pageWindow.require?.('discourse/helpers/category-link');
            if (categoryLinkHelper?.categoryBadgeHTML) {
                const html = categoryLinkHelper.categoryBadgeHTML(cat._emberModel || cat, {
                    allowUncategorized: true,
                    link: true,
                    hideParent: true,
                });
                if (html) {
                    const temp = document.createElement('span');
                    temp.innerHTML = html;
                    const badgeEl = temp.firstElementChild;
                    if (badgeEl) {
                        badgeEl.addEventListener('click', (e) => navigateTo(e, badgeEl.getAttribute('href')));
                        return badgeEl;
                    }
                }
            }
        } catch {
            // fallback below
        }

        // 兼容新旧 Discourse 主题的 DOM 回退
        const wrapper = document.createElement('a');
        const sampleBadge = document.querySelector('.topic-list .badge-category__wrapper, .topic-list .badge-wrapper');
        if (sampleBadge) {
            wrapper.className = sampleBadge.className;
        } else {
            const catStyle = getSiteSettings().category_style || 'box';
            wrapper.className = `badge-category__wrapper ${catStyle}`;
        }
        wrapper.style.setProperty('--category-badge-color', `#${cat.color || '0088cc'}`);
        wrapper.style.setProperty('--category-badge-text-color', `#${cat.text_color || 'FFFFFF'}`);
        wrapper.href = parentCat ? `/c/${parentCat.slug}/${cat.slug}/${cat.id}` : `/c/${cat.slug}/${cat.id}`;
        wrapper.addEventListener('click', (e) => navigateTo(e, wrapper.getAttribute('href')));

        if (wrapper.classList.contains('badge-wrapper')) {
            const bg = document.createElement('span');
            bg.className = 'badge-category-bg';
            bg.style.backgroundColor = `#${cat.color || '0088cc'}`;
            wrapper.appendChild(bg);

            const clearBadge = document.createElement('span');
            clearBadge.className = 'badge-category clear-badge';
            const nameSpan = document.createElement('span');
            nameSpan.className = 'badge-category__name';
            nameSpan.textContent = cat.name;
            clearBadge.appendChild(nameSpan);
            wrapper.appendChild(clearBadge);
        } else {
            const badgeSpan = document.createElement('span');
            badgeSpan.className = `badge-category --style-${cat.style_type || 'square'}`;
            badgeSpan.setAttribute('data-category-id', String(cat.id));
            const nameSpan = document.createElement('span');
            nameSpan.className = 'badge-category__name';
            nameSpan.textContent = cat.name;
            badgeSpan.appendChild(nameSpan);
            wrapper.appendChild(badgeSpan);
        }

        return wrapper;
    };

    // 回溯完整的父子分类链，依次生成父分类与子分类节点（如：■ 水源站务 ■ 站点反馈）
    const buildCategoryBadgesFragment = (categoryId) => {
        if (!categoryId) return null;
        const categoriesMap = getCategoriesMap();
        const targetCat = categoriesMap.get(Number(categoryId));
        if (!targetCat) return null;

        const chain = [];
        let curr = targetCat;
        const visited = new Set();
        while (curr && !visited.has(curr.id)) {
            visited.add(curr.id);
            chain.unshift(curr);
            const parentId = curr.parent_category_id ? Number(curr.parent_category_id) : null;
            curr = parentId ? categoriesMap.get(parentId) : null;
        }

        const fragment = document.createDocumentFragment();
        for (let i = 0; i < chain.length; i++) {
            const cat = chain[i];
            const parentCat = i > 0 ? chain[i - 1] : null;
            const badgeNode = buildSingleCategoryBadge(cat, parentCat);
            if (badgeNode) {
                fragment.appendChild(badgeNode);
            }
        }
        return fragment;
    };

    const buildTagsNode = (tags) => {
        const normalizedTags = normalizeTagsArray(tags);
        if (normalizedTags.length === 0) return null;

        const container = document.createElement('div');
        container.className = 'discourse-tags';
        container.setAttribute('role', 'list');

        // 优先从页面已有标签或站点设置获取当前主题的 tag_style（如 box / bullet / simple）
        const sampleTag = document.querySelector('.topic-list .discourse-tag');
        const tagStyle = getSiteSettings().tag_style || 'box';
        const tagClass = sampleTag ? sampleTag.className : `discourse-tag ${tagStyle}`;

        for (const tagObj of normalizedTags) {
            let tagEl = null;
            try {
                const renderTag = pageWindow.require?.('discourse/lib/render-tag')?.default;
                if (typeof renderTag === 'function') {
                    const html = renderTag(tagObj.name, { style: tagStyle });
                    if (html) {
                        const temp = document.createElement('span');
                        temp.innerHTML = html;
                        tagEl = temp.firstElementChild;
                    }
                }
            } catch {
                // fallback below
            }

            if (!tagEl) {
                tagEl = document.createElement('a');
                tagEl.className = tagClass;
                tagEl.href = `/tag/${encodeURIComponent(tagObj.slug)}`;
                tagEl.setAttribute('data-tag-name', tagObj.name);
                tagEl.textContent = tagObj.name;
            }
            tagEl.addEventListener('click', (e) => navigateTo(e, tagEl.getAttribute('href')));
            container.appendChild(tagEl);
            container.appendChild(document.createTextNode(' '));
        }
        return container;
    };

    // 解析表头列结构，确保在任何自定义主题下都能严格对齐列顺序
    const detectTableColumnTypes = (table) => {
        const ths = table ? [...table.querySelectorAll('thead tr th')] : [];
        if (ths.length === 0) {
            return ['default', 'posters', 'posts', 'views', 'activity'];
        }
        return ths.map((th) => {
            const sortOrder = th.getAttribute('data-sort-order') || '';
            if (th.classList.contains('bulk-select')) return 'bulk-select';
            if (sortOrder === 'default' || th.classList.contains('default') || th.classList.contains('main-link') || th.classList.contains('topics')) {
                return 'default';
            }
            if (sortOrder === 'posters' || th.classList.contains('posters')) return 'posters';
            if (sortOrder === 'posts' || th.classList.contains('posts') || th.classList.contains('replies')) return 'posts';
            if (sortOrder === 'views' || th.classList.contains('views')) return 'views';
            if (sortOrder === 'activity' || th.classList.contains('activity')) return 'activity';
            return 'unknown';
        });
    };

    const buildPinnedTopicRow = (record, columnTypes) => {
        // 渲染只读取缓存，不从可能过期的原生列表或跟踪器反写未读状态。
        const tr = document.createElement('tr');
        const unreadCount = Number(record.unread_posts) || 0;
        tr.className = `topic-list-item category-${record.category_id || 'none'} ${unreadCount > 0 ? 'unread' : 'visited'} ember-view shuiyuan-pin-row`;
        tr.setAttribute('data-topic-id', String(record.id));

        const lastRead = record.last_read_post_number || 1;
        const highestPost = record.highest_post_number || 1;
        const firstUnreadPost = unreadCount > 0 ? Math.min(highestPost, lastRead + 1) : lastRead;
        const titleTargetUrl = `/t/${record.slug || 'topic'}/${record.id}/${firstUnreadPost}`;
        const latestPostUrl = `/t/${record.slug || 'topic'}/${record.id}/${highestPost}`;

        // 移动端视图渲染
        if (IS_MOBILE_VIEW()) {
            const td = document.createElement('td');
            td.className = 'topic-list-data';

            const rightDiv = document.createElement('div');
            rightDiv.className = 'right';

            const mainLinkDiv = document.createElement('div');
            mainLinkDiv.className = 'main-link';

            const unpinSpan = document.createElement('span');
            unpinSpan.className = 'topic-status shuiyuan-unpin-trigger';
            unpinSpan.title = '常驻未读话题（点击移出）';
            unpinSpan.innerHTML = THUMBTACK_ICON;
            unpinSpan.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                togglePinTopic(record.id);
            });
            mainLinkDiv.appendChild(unpinSpan);

            const titleLink = document.createElement('a');
            titleLink.href = titleTargetUrl;
            titleLink.className = 'title raw-link raw-topic-link';
            titleLink.setAttribute('data-topic-id', String(record.id));
            setTitleElementWithEmojis(titleLink, record);
            titleLink.addEventListener('click', (e) => navigateTo(e, titleTargetUrl));
            mainLinkDiv.appendChild(titleLink);

            if (unreadCount > 0) {
                const badgeWrap = document.createElement('span');
                badgeWrap.className = 'topic-post-badges';
                badgeWrap.appendChild(document.createTextNode('\u00A0'));
                const unreadA = document.createElement('a');
                unreadA.href = titleTargetUrl;
                unreadA.title = `${unreadCount} 个未读帖子`;
                unreadA.className = 'badge badge-notification unread-posts';
                unreadA.textContent = String(unreadCount);
                unreadA.addEventListener('click', (e) => navigateTo(e, titleTargetUrl));
                badgeWrap.appendChild(unreadA);
                mainLinkDiv.appendChild(badgeWrap);
            }

            rightDiv.appendChild(mainLinkDiv);

            const bottomLine = document.createElement('div');
            bottomLine.className = 'link-bottom-line';
            const catBadges = buildCategoryBadgesFragment(record.category_id);
            if (catBadges) {
                bottomLine.appendChild(catBadges);
            }
            const tagsNode = buildTagsNode(record.tags);
            if (tagsNode) {
                bottomLine.appendChild(tagsNode);
            }
            if (bottomLine.childNodes.length > 0) {
                rightDiv.appendChild(bottomLine);
            }

            const pullRight = document.createElement('div');
            pullRight.className = 'pull-right';
            const numSpan = document.createElement('span');
            numSpan.className = 'num activity last';
            const ageA = document.createElement('a');
            ageA.href = latestPostUrl;
            ageA.className = 'badge-posts';
            ageA.textContent = formatRelativeTime(record.last_posted_at);
            ageA.addEventListener('click', (e) => navigateTo(e, latestPostUrl));
            numSpan.appendChild(ageA);
            pullRight.appendChild(numSpan);
            rightDiv.appendChild(pullRight);

            td.appendChild(rightDiv);
            tr.appendChild(td);
            return tr;
        }

        // 桌面端视图渲染：根据当前主题的表头列顺序动态构建单元格
        const cellBuilders = {
            'bulk-select': () => {
                const bulkTd = document.createElement('td');
                bulkTd.className = 'bulk-select topic-list-data';
                return bulkTd;
            },
            'default': () => {
                const mainTd = document.createElement('td');
                mainTd.className = 'main-link clearfix topic-list-data';
                mainTd.colSpan = 1;

                const topLine = document.createElement('span');
                topLine.className = 'link-top-line';

                const topicStatuses = document.createElement('span');
                topicStatuses.className = 'topic-statuses';
                const unpinTrigger = document.createElement('span');
                unpinTrigger.className = 'topic-status shuiyuan-unpin-trigger';
                unpinTrigger.title = '常驻未读话题（点击移出）';
                unpinTrigger.innerHTML = THUMBTACK_ICON;
                unpinTrigger.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    togglePinTopic(record.id);
                });
                topicStatuses.appendChild(unpinTrigger);
                topLine.appendChild(topicStatuses);

                const titleA = document.createElement('a');
                titleA.href = titleTargetUrl;
                titleA.className = 'title raw-link raw-topic-link';
                titleA.setAttribute('data-topic-id', String(record.id));
                setTitleElementWithEmojis(titleA, record);
                titleA.addEventListener('click', (e) => navigateTo(e, titleTargetUrl));
                topLine.appendChild(titleA);

                if (unreadCount > 0) {
                    const postBadges = document.createElement('span');
                    postBadges.className = 'topic-post-badges';
                    postBadges.appendChild(document.createTextNode('\u00A0'));
                    const unreadBadge = document.createElement('a');
                    unreadBadge.href = titleTargetUrl;
                    unreadBadge.title = `${unreadCount} 个未读帖子`;
                    unreadBadge.className = 'badge badge-notification unread-posts';
                    unreadBadge.textContent = String(unreadCount);
                    unreadBadge.addEventListener('click', (e) => navigateTo(e, titleTargetUrl));
                    postBadges.appendChild(unreadBadge);
                    topLine.appendChild(postBadges);
                }

                mainTd.appendChild(topLine);

                const bottomLine = document.createElement('div');
                bottomLine.className = 'link-bottom-line';
                const catBadges = buildCategoryBadgesFragment(record.category_id);
                if (catBadges) {
                    bottomLine.appendChild(catBadges);
                }
                const tagsNode = buildTagsNode(record.tags);
                if (tagsNode) {
                    bottomLine.appendChild(tagsNode);
                }
                if (bottomLine.childNodes.length > 0) {
                    mainTd.appendChild(bottomLine);
                }
                return mainTd;
            },
            'posters': () => {
                const postersTd = document.createElement('td');
                postersTd.className = 'posters topic-list-data';
                for (const p of (record.posters || []).slice(0, 5)) {
                    const userA = document.createElement('a');
                    userA.href = `/u/${encodeURIComponent(p.username)}`;
                    userA.setAttribute('data-user-card', p.username);
                    if (p.isLatest) {
                        userA.className = 'latest';
                    }
                    const img = document.createElement('img');
                    img.alt = '';
                    img.width = 24;
                    img.height = 24;
                    img.loading = 'lazy';
                    let avatarSrc = (p.avatar_template || '/images/avatar.png').replace('{size}', '48');
                    if (!avatarSrc.startsWith('http') && !avatarSrc.startsWith('/')) {
                        avatarSrc = `/${avatarSrc}`;
                    }
                    img.src = avatarSrc;
                    img.className = p.isLatest ? 'avatar latest' : 'avatar';
                    img.title = p.username;
                    userA.appendChild(img);
                    postersTd.appendChild(userA);
                }
                return postersTd;
            },
            'posts': () => {
                const replies = Math.max(0, (record.posts_count ?? 1) - 1);
                const postsHeatmap = getPostsHeatmapClass(replies);
                const postsTd = document.createElement('td');
                postsTd.className = `num posts-map posts ${postsHeatmap} topic-list-data`.trim();
                postsTd.title = `${replies} 个回复`;
                const postsBtn = document.createElement('a');
                postsBtn.href = titleTargetUrl;
                postsBtn.className = `posts-map badge-posts ${postsHeatmap}`.trim();
                postsBtn.addEventListener('click', (e) => navigateTo(e, titleTargetUrl));
                const postsNumSpan = document.createElement('span');
                postsNumSpan.className = 'number';
                postsNumSpan.textContent = formatCount(replies);
                postsBtn.appendChild(postsNumSpan);
                postsTd.appendChild(postsBtn);
                return postsTd;
            },
            'views': () => {
                const views = record.views ?? 0;
                const viewsHeatmap = getViewsHeatmapClass(views);
                const viewsTd = document.createElement('td');
                viewsTd.className = `num views ${viewsHeatmap} topic-list-data`.trim();
                const viewsSpan = document.createElement('span');
                viewsSpan.className = 'number';
                viewsSpan.title = `此话题已被浏览 ${views} 次`;
                viewsSpan.textContent = formatCount(views);
                viewsTd.appendChild(viewsSpan);
                return viewsTd;
            },
            'activity': () => {
                const activityTd = document.createElement('td');
                activityTd.className = 'age activity topic-list-data';
                const activityA = document.createElement('a');
                activityA.className = 'post-activity';
                activityA.href = latestPostUrl;
                activityA.addEventListener('click', (e) => navigateTo(e, latestPostUrl));
                const relSpan = document.createElement('span');
                relSpan.className = 'relative-date';
                relSpan.textContent = formatRelativeTime(record.last_posted_at);
                activityA.appendChild(relSpan);
                activityTd.appendChild(activityA);
                return activityTd;
            },
            'unknown': () => {
                const emptyTd = document.createElement('td');
                emptyTd.className = 'topic-list-data';
                return emptyTd;
            },
        };

        for (const colType of columnTypes) {
            const builder = cellBuilders[colType] || cellBuilders.unknown;
            tr.appendChild(builder());
        }

        return tr;
    };

    // 清理未读列表中的常驻节点与隐藏状态（在切换到其它标签页如“最新/新”时调用）
    const cleanupPinnedRows = () => {
        mutateDOM(() => {
            for (const el of document.querySelectorAll('.shuiyuan-pin-row, .shuiyuan-pin-separator, table.shuiyuan-pin-custom-table')) {
                el.remove();
            }
            for (const hiddenRow of document.querySelectorAll('tr.topic-list-item.shuiyuan-pin-hidden-native')) {
                hiddenRow.classList.remove('shuiyuan-pin-hidden-native');
            }
        });
    };

    // 当未读页原本没有任何未读话题时，构建原生表头容器
    const ensureTopicListTableOnEmptyUnread = () => {
        const contents = document.querySelector('.list-container .contents');
        if (!contents) return null;

        // 返回时原生表格可能稍后才恢复；它出现后应接管临时表格。
        const nativeTable = contents.querySelector('table.topic-list:not(.shuiyuan-pin-custom-table)');
        if (nativeTable) {
            for (const customTable of contents.querySelectorAll('table.shuiyuan-pin-custom-table')) {
                customTable.remove();
            }
            return nativeTable;
        }
        let table = contents.querySelector('table.shuiyuan-pin-custom-table');
        if (table) return table;

        table = document.createElement('table');
        table.className = 'topic-list ember-view shuiyuan-pin-custom-table';
        if (IS_MOBILE_VIEW()) {
            table.innerHTML = `<tbody class="topic-list-body"></tbody>`;
        } else {
            table.innerHTML = `
                <thead class="topic-list-header">
                    <tr>
                        <th data-sort-order="default" class="default topic-list-data" scope="col"><span>话题</span></th>
                        <th data-sort-order="posters" class="posters topic-list-data" scope="col"><span class="sr-only">发帖人</span></th>
                        <th data-sort-order="posts" class="posts sortable num topic-list-data" scope="col"><span>回复</span></th>
                        <th data-sort-order="views" class="views sortable num topic-list-data" scope="col"><span>浏览量</span></th>
                        <th data-sort-order="activity" class="activity sortable num topic-list-data" scope="col"><span>活动</span></th>
                    </tr>
                </thead>
                <tbody class="topic-list-body"></tbody>
            `;
        }
        contents.prepend(table);
        return table;
    };

    // 在 /unread 页面渲染所有常驻的话题
    const renderPinnedTopicsOnUnreadPage = () => {
        if (isPageTransitioning()) return;
        if (!isUnreadPage()) {
            cleanupPinnedRows();
            return;
        }

        const pinnedMap = loadPinnedMap();
        if (pinnedMap.size === 0) {
            cleanupPinnedRows();
            return;
        }

        const table = mutateDOM(ensureTopicListTableOnEmptyUnread);
        const tbody = table?.querySelector('tbody.topic-list-body') || table?.querySelector('tbody');
        if (!tbody) return;

        mutateDOM(() => {
            // 移除旧的常驻行与分隔线
            for (const el of tbody.querySelectorAll('.shuiyuan-pin-row, .shuiyuan-pin-separator')) {
                el.remove();
            }

            // 恢复并重新检查原生行是否与常驻话题重复
            for (const nativeRow of tbody.querySelectorAll('tr.topic-list-item:not(.shuiyuan-pin-row)')) {
                const tid = parseInt(nativeRow.getAttribute('data-topic-id'), 10);
                if (pinnedMap.has(tid)) {
                    nativeRow.classList.add('shuiyuan-pin-hidden-native');
                } else {
                    nativeRow.classList.remove('shuiyuan-pin-hidden-native');
                }
            }

            const columnTypes = detectTableColumnTypes(table);
            const colCount = IS_MOBILE_VIEW() ? 1 : (columnTypes.length || 5);
            const fragment = document.createDocumentFragment();

            // 按置顶时间倒序（最新置顶的排在最上方）
            const sortedRecords = [...pinnedMap.values()].sort((a, b) => (b.pinned_at || 0) - (a.pinned_at || 0));
            for (const rec of sortedRecords) {
                fragment.appendChild(buildPinnedTopicRow(rec, columnTypes));
            }

            // 如果下方还有未隐藏的普通未读话题，则插入一条原生分隔线隔开
            const hasVisibleNativeUnread = Boolean(
                tbody.querySelector('tr.topic-list-item:not(.shuiyuan-pin-row):not(.shuiyuan-pin-hidden-native)')
            );
            if (hasVisibleNativeUnread) {
                const sepTr = document.createElement('tr');
                sepTr.className = 'topic-list-item-separator shuiyuan-pin-separator';
                const sepTd = document.createElement('td');
                sepTd.className = 'topic-list-data';
                sepTd.colSpan = colCount;
                sepTr.appendChild(sepTd);
                fragment.appendChild(sepTr);
            }

            tbody.prepend(fragment);
        });
    };

    // 后台异步刷新所有常驻话题的最新状态与未读条数
    const refreshPinnedTopicsData = async ({ force = false } = {}) => {
        if (!isUnreadPage() || isPageTransitioning()) return;
        if (isRefreshing) {
            pendingForcedRefresh ||= force;
            return;
        }
        const pinnedMap = loadPinnedMap();
        if (pinnedMap.size === 0) return;

        const now = Date.now();
        const idsToFetch = [...pinnedMap.keys()].filter(
            (id) => force || now - (lastRefreshTimeMap.get(id) || 0) > REFRESH_COOLDOWN_MS
        );
        if (idsToFetch.length === 0) return;

        isRefreshing = true;
        let hasUpdates = false;
        try {
            for (let i = 0; i < idsToFetch.length; i += FETCH_CONCURRENCY) {
                const batch = idsToFetch.slice(i, i + FETCH_CONCURRENCY);
                // eslint-disable-next-line no-await-in-loop
                await Promise.allSettled(
                    batch.map(async (id) => {
                        const data = await discourseFetchJSON(`/t/${id}.json?track_visit=false`);
                        const latestMap = loadPinnedMap();
                        if (latestMap.has(id)) {
                            const updatedRec = parseTopicJSONToRecord(data, latestMap.get(id));
                            latestMap.set(id, updatedRec);
                            savePinnedMap(latestMap);
                            lastRefreshTimeMap.set(id, Date.now());
                            hasUpdates = true;
                        }
                    })
                );
            }
            if (hasUpdates && isUnreadPage()) {
                renderPinnedTopicsOnUnreadPage();
            }
        } catch (e) {
            console.error('[水源未读常驻] 刷新常驻话题数据出错:', e);
        } finally {
            isRefreshing = false;
            // 返回页面时若上一轮请求尚未结束，完成后补一次刷新。
            if (pendingForcedRefresh) {
                pendingForcedRefresh = false;
                refreshPinnedTopicsData({ force: true });
            }
        }
    };

    // ==================== 路由与 DOM 变化监听（跨浏览器兼容） ====================
    let scheduledCheck = false;
    let wasOnUnreadPage = false;
    const schedulePageUpdate = () => {
        if (scheduledCheck || isMutatingDOM) return;
        scheduledCheck = true;
        requestAnimationFrame(() => {
            scheduledCheck = false;
            if (isPageTransitioning()) return;
            mutateDOM(injectTopicHeaderPinButtons);
            if (isUnreadPage()) {
                const enteringUnreadPage = !wasOnUnreadPage;
                wasOnUnreadPage = true;
                renderPinnedTopicsOnUnreadPage();
                // 路由返回时必须读取最新进度，不能被普通 DOM 更新的冷却时间拦住。
                refreshPinnedTopicsData({ force: enteringUnreadPage });
            } else {
                wasOnUnreadPage = false;
                cleanupPinnedRows();
            }
        });
    };

    // 1. 监听 History API 路由切换
    for (const method of ['pushState', 'replaceState']) {
        const orig = window.history[method];
        window.history[method] = function (...args) {
            const ret = orig.apply(this, args);
            if (!isUnreadPage()) wasOnUnreadPage = false;
            schedulePageUpdate();
            return ret;
        };
    }
    window.addEventListener('popstate', () => {
        if (!isUnreadPage()) wasOnUnreadPage = false;
        schedulePageUpdate();
    });
    window.addEventListener('pageshow', (event) => {
        if (event.persisted) {
            wasOnUnreadPage = false;
            schedulePageUpdate();
        }
    });

    // 2. 尝试挂载 Discourse Ember Router 事件
    let routerHooked = false;
    const tryHookDiscourseRouter = () => {
        if (routerHooked) return;
        try {
            const router = getDiscourseRouter();
            if (router?.on) {
                router.on('routeWillChange', () => {
                    isRouteTransitioning = true;
                    wasOnUnreadPage = false;
                });
                router.on('routeDidChange', () => {
                    isRouteTransitioning = false;
                    schedulePageUpdate();
                });
                routerHooked = true;
            }
        } catch {
            // ignore
        }
    };

    // 3. 监听 DOM 变化（过滤掉脚本自身插入的节点，防止死循环）
    pageObserver = new MutationObserver((mutations) => {
        if (!routerHooked) {
            tryHookDiscourseRouter();
        }
        if (isMutatingDOM) return;
        for (const m of mutations) {
            const target = m.target.nodeType === Node.ELEMENT_NODE ? m.target : m.target.parentElement;
            if (target?.closest('.shuiyuan-pin-row, .shuiyuan-pin-separator, .shuiyuan-pin-btn')) {
                continue;
            }
            // 也处理列表恢复时的删除和文字更新，不能只监听新增元素。
            schedulePageUpdate();
            return;
        }
    });

    pageObserver.observe(document.documentElement, observerOptions);

    // 初始执行
    tryHookDiscourseRouter();
    schedulePageUpdate();
})();
