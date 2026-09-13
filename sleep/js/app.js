/* ==================== app.js — 全局逻辑 ==================== */

// 全局工具
const App = {
  // 页面切换
  switchPage(pageName) {
    document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
    const target = document.getElementById('page-' + pageName);
    if (target) {
      target.classList.remove('hidden');
      target.scrollIntoView({ top: 0, behavior: 'instant' });
    }
    // 更新底部导航
    document.querySelectorAll('.tabbar-item').forEach(item => {
      item.classList.toggle('active', item.dataset.page === pageName);
    });
    // 通知各模块
    if (pageName === 'diary' && typeof Diary !== 'undefined') Diary.refresh();
    if (pageName === 'profile' && typeof Profile !== 'undefined') Profile.refresh();
    if (pageName === 'science' && typeof Science !== 'undefined') Science.refresh();
    if (pageName === 'audio' && typeof AudioModule !== 'undefined') AudioModule.refreshList();
  },

  // Toast 提示
  toast(msg, duration) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.classList.remove('hidden');
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => {
      el.classList.add('hidden');
    }, duration || 2000);
  },

  // localStorage 封装
  store: {
    get(key, def) {
      try {
        const v = localStorage.getItem(key);
        return v ? JSON.parse(v) : def;
      } catch (e) {
        return def;
      }
    },
    set(key, val) {
      try {
        localStorage.setItem(key, JSON.stringify(val));
      } catch (e) {
        console.warn('localStorage 写入失败', e);
      }
    },
    remove(key) {
      localStorage.removeItem(key);
    },
    clear() {
      localStorage.clear();
    }
  },

  // 日期工具
  formatDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  },

  // 今日种子（用于每日贴士）
  todaySeed() {
    const d = new Date();
    return d.getFullYear() * 1000 + d.getMonth() * 50 + d.getDate();
  },

  // 分享功能
  share() {
    const url = window.location.href;
    const shareModal = document.getElementById('share-modal');
    const linkInput = document.getElementById('share-link-input');
    if (shareModal && linkInput) {
      linkInput.value = url;
      shareModal.classList.remove('hidden');
    }
  },

  copyLink() {
    const input = document.getElementById('share-link-input');
    const tip = document.getElementById('share-modal-tip');
    if (!input) return;
    input.select();
    input.setSelectionRange(0, 99999);
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch (e) {
      ok = false;
    }
    if (ok && tip) {
      tip.textContent = '链接已复制，快去分享吧！';
      tip.style.color = 'var(--green)';
    } else if (tip) {
      tip.textContent = '复制失败，请手动长按选中链接复制';
      tip.style.color = 'var(--danger)';
    }
  },

  closeShare() {
    const shareModal = document.getElementById('share-modal');
    const tip = document.getElementById('share-modal-tip');
    if (shareModal) shareModal.classList.add('hidden');
    if (tip) tip.textContent = '';
  },

  // 记录首次使用
  initFirstUse() {
    const first = this.store.get('ynhm_first_use', null);
    if (!first) {
      this.store.set('ynhm_first_use', this.formatDate(new Date()));
    }
  },

  // 获取使用天数
  getUseDays() {
    const first = this.store.get('ynhm_first_use', this.formatDate(new Date()));
    const d1 = new Date(first);
    const d2 = new Date();
    return Math.max(1, Math.floor((d2 - d1) / 86400000) + 1);
  }
};

// 每日睡眠小贴士
const DAILY_TIPS = [
  '睡前1小时关掉蓝光屏幕，让褪黑素自然分泌，困意会来得更快。',
  '卧室温度保持在18-22°C最利于入睡，太热或太冷都会让你辗转反侧。',
  '下午3点后避免咖啡因，它的半衰期长达6小时，晚上可能还在"加班"。',
  '固定时间上床和起床，哪怕周末也一样——生物钟喜欢规律。',
  '睡不着别硬躺，起来做点放松的事，20分钟后再回床上。',
  '睡前泡脚15分钟能让体表升温，随后散热会帮助核心体温下降，催生睡意。',
  '白噪音可以掩盖环境突响，让大脑不去"监听"外界，更容易沉入深睡。',
  '深呼吸激活副交感神经：吸气4秒、屏息7秒、呼气8秒，重复4次。',
  '睡前别吃太饱，但饿着也不行——一杯温牛奶或几颗坚果是不错的选择。',
  '把焦虑写下来，告诉大脑"已经记好了明天再处理"，减轻入睡时的反刍思维。',
  '左侧卧能减轻胃酸反流，仰卧适合颈椎不好的人，蜷缩姿势反而更放松。',
  '薰衣草精油滴在枕边，其芳樟醇成分被证实能降低心率、助眠安神。',
  '午睡别超过30分钟，否则进入深睡后被叫醒，反而昏沉一下午。',
  '运动帮助睡眠，但睡前2小时内剧烈运动会让核心体温升高，适得其反。',
  '把手机充电器放客厅，卧室只用来睡觉——经典的"刺激控制疗法"。'
];

function loadDailyTip() {
  const seed = App.todaySeed();
  const tip = DAILY_TIPS[seed % DAILY_TIPS.length];
  const el = document.getElementById('daily-tip');
  if (el) el.textContent = tip;
}

// 事件绑定
document.addEventListener('DOMContentLoaded', function () {
  App.initFirstUse();
  loadDailyTip();

  // 首页宫格导航
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      App.switchPage(item.dataset.page);
    });
  });

  // 返回按钮
  document.querySelectorAll('.back-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      App.switchPage(btn.dataset.page);
    });
  });

  // 底部导航
  document.querySelectorAll('.tabbar-item').forEach(item => {
    item.addEventListener('click', () => {
      App.switchPage(item.dataset.page);
    });
  });

  // 首页快捷按钮
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.audio && typeof AudioModule !== 'undefined') {
        App.switchPage('audio');
        setTimeout(() => AudioModule.playByTag(btn.dataset.audio), 300);
      } else if (btn.dataset.page) {
        App.switchPage(btn.dataset.page);
      }
    });
  });

  // 分享按钮
  const shareBtn = document.getElementById('share-btn');
  if (shareBtn) {
    shareBtn.addEventListener('click', () => App.share());
  }
  const copyBtn = document.getElementById('copy-link-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => App.copyLink());
  }
  const shareCloseBtn = document.getElementById('share-close-btn');
  if (shareCloseBtn) {
    shareCloseBtn.addEventListener('click', () => App.closeShare());
  }
  const shareMask = document.getElementById('share-modal-mask');
  if (shareMask) {
    shareMask.addEventListener('click', () => App.closeShare());
  }

  // 微信环境下的分享引导
  if (typeof wx !== 'undefined' && wx.config) {
    wx.config({
      debug: false,
      appId: '',
      timestamp: 0,
      nonceStr: '',
      signature: '',
      jsApiList: ['updateAppMessageShareData', 'updateTimelineShareData']
    });
    wx.ready(function () {
      const shareData = {
        title: '一念好眠 · 睡前助手',
        desc: '睡前30分钟，让心静下来',
        link: window.location.href,
        imgUrl: ''
      };
      wx.updateAppMessageShareData(shareData);
      wx.updateTimelineShareData(shareData);
    });
  }
});
