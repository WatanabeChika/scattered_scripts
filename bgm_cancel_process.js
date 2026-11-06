// ==UserScript==
// @name          点击在看时自动撤销所有进度
// @version       1.0.0
// @description   在 Bangumi 上将条目标为“在看”时，如果目前所有单集（不含SP）都被标记过“看过”，则自动撤销所有单集的“看过”状态。
// @include       /^https://[^/]*/subject/[^/]*$/
// ==/UserScript==

(() => {
  function getSubjectType() {
    const typeRegex = /Bangumi (\S*) Ranked:/g;
    const typeEl = $(
      'div.global_rating > div.global_score > div > small.grey',
    ).text();
    const match = typeRegex.exec(typeEl);
    return match ? match[1] : null;
  }

  // 并检查是否所有正片单集都已经看过
  function getMainEpisodesInfo() {
    let ids = [];
    let isAllWatched = true;
    const allEp = $('ul.prg_list li');
    let splitIndex = 0;

    // 找到第一个 SP 的位置来分隔正片
    allEp.each(function (index, value) {
      const el = $(value);
      if (el.hasClass('subtitle')) {
        if (splitIndex === 0) {
          splitIndex = index;
        }
      }
    });
    if (splitIndex === 0) {
      splitIndex = allEp.length;
    }

    // 截取所有正片单集的元素
    const mainEps = allEp.slice(0, splitIndex).find('a.load-epinfo');
    if (mainEps.length === 0) {
      return { ids: [], isAllWatched: false };
    }

    // 遍历正片，收集 ID 并判断是否全部含有 "epBtnWatched"（即看过状态）
    mainEps.each(function () {
      const a = $(this);
      ids.push(a.attr('id').split('_').pop());
      if (!a.hasClass('epBtnWatched')) {
        isAllWatched = false;
      }
    });

    return { ids, isAllWatched };
  }

  // 逐集撤销看过状态，并实时更新按钮文字
  async function animeUnmarkWatched(form, ids, submitBtn) {
    const submitGh = form.attr('action').split('?gh=').pop();
    const total = ids.length;
    let count = 0;
    
    for (const id of ids) {
      count++;
      submitBtn.attr('value', `撤销进度 (${count}/${total})...`);
      
      await fetch(`/subject/ep/${id}/status/remove?gh=${submitGh}&ajax=1`, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        method: 'POST',
      });
      // 增加 50 毫秒延时
      await new Promise(resolve => setTimeout(resolve, 50));
    }
  }

  const type = getSubjectType();
  // 非 Anime 和 Real 则不执行
  if (!(type === 'Anime' || type === 'Real')) {
    return;
  }

  document.addEventListener('click', function (e) {
    const target = $(e.target);
    const form = $('#collectBoxForm');

    // 监听保存按钮的点击事件，并且必须是选中“在看”（id 为 'do'）
    if (
      target.hasClass('inputBtn') &&
      target.attr('type') === 'submit' &&
      target.attr('name') === 'update' &&
      $('#do').is(':checked')
    ) {
      const { ids, isAllWatched } = getMainEpisodesInfo();

      // 判断核心条件：存在集数，且全都被标记为了“看过”
      if (ids.length > 0 && isAllWatched) {
        // 阻止默认表单提交，方便先处理撤销进度的异步请求
        form.on('submit', function () {
          return false;
        });
        e.preventDefault();
        
        // 修改 UI 状态为正在加载
        target.prop('disabled', true);
        target.css({
          'background': '#e2e2e2',
          'color': '#888',
          'cursor': 'wait',
          'border': '1px solid #ccc',
          'box-shadow': 'none'
        });

        // 传入 target（即保存按钮）以便在函数内部更新文字进度
        animeUnmarkWatched(form, ids, target)
          .then(() => {
            target.attr('value', '正在保存状态...'); 
            // 提交“修改条目状态为在看”表单
            $.post(form.attr('action'), form.serialize()).done(() => {
              target.attr('value', '完成！'); 
              location.reload();
            });
          })
          .catch((err) => {
            if (err) {
              console.error('撤销进度时发生错误:', err);
              target.attr('value', '网络错误，请重试');
              target.prop('disabled', false);
              target.css({
                'background': '', 
                'color': '',
                'cursor': 'pointer',
                'border': '',
                'box-shadow': ''
              });
            }
          });
      }
    }
  });
})();