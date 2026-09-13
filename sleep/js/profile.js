/* ==================== profile.js — 个人中心 ==================== */

const Profile = {
  init() {
    this.bindEvents();
  },

  bindEvents() {
    // 清除数据
    document.getElementById('profile-clear').addEventListener('click', () => {
      this.showConfirm();
    });

    // 关于
    document.getElementById('profile-about').addEventListener('click', () => {
      this.showAbout();
    });
  },

  refresh() {
    const days = App.getUseDays();
    document.getElementById('profile-days').textContent = '\u5df2\u4f7f\u7528 ' + days + ' \u5929';

    // 统计
    const diary = App.store.get('ynhm_diary', []);
    const totalRecords = diary.length;
    const avgRating = totalRecords > 0
      ? (diary.reduce((s, r) => s + r.rating, 0) / totalRecords).toFixed(1)
      : '0.0';

    // 音频播放次数
    const playCount = App.store.get('ynhm_play_count', 0);
    // 呼吸练习次数
    const breathCount = App.store.get('ynhm_breath_count', 0);

    const statsEl = document.getElementById('profile-stats');
    statsEl.innerHTML =
      '<div class="stat-card"><div class="stat-value">' + totalRecords + '</div><div class="stat-label">日记记录</div></div>' +
      '<div class="stat-card"><div class="stat-value">' + avgRating + '</div><div class="stat-label">平均评分</div></div>' +
      '<div class="stat-card"><div class="stat-value">' + days + '</div><div class="stat-label">使用天数</div></div>';
  },

  showAbout() {
    // 创建弹窗
    let modal = document.getElementById('about-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'about-modal';
      modal.className = 'about-modal';
      modal.innerHTML =
        '<div class="about-content">' +
        '<h3>\u4e00\u5ff5\u597d\u7720</h3>' +
        '<p>\u7761\u524d30\u5206\u949f\uff0c\u8ba9\u5fc3\u9759\u4e0b\u6765</p>' +
        '<p>\u52a9\u7720\u97f3\u5e93 \u00b7 478\u547c\u5438\u6cd5 \u00b7 \u7761\u7720\u65e5\u8bb0 \u00b7 \u7761\u7720\u79d1\u666e</p>' +
        '<p>\u613f\u4f60\u6bcf\u4e00\u4e2a\u591c\u665a\u90fd\u80fd\u597d\u7720</p>' +
        '<p class="about-version">Version 1.0.0</p>' +
        '<button class="about-close">\u77e5\u9053\u4e86</button>' +
        '</div>';
      document.body.appendChild(modal);
      modal.querySelector('.about-close').addEventListener('click', () => {
        modal.classList.add('hidden');
      });
    }
    modal.classList.remove('hidden');
  },

  showConfirm() {
    let modal = document.getElementById('confirm-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'confirm-modal';
      modal.className = 'confirm-modal';
      modal.innerHTML =
        '<div class="confirm-content">' +
        '<p>\u786e\u5b9a\u8981\u6e05\u9664\u6240\u6709\u6570\u636e\u5417\uff1f<br>\u7761\u7720\u65e5\u8bb0\u3001\u4f7f\u7528\u8bb0\u5f55\u7b49\u5c06\u5168\u90e8\u5220\u9664\uff0c\u4e14\u4e0d\u53ef\u6062\u590d\u3002</p>' +
        '<div class="confirm-buttons">' +
        '<button class="btn-cancel">\u518d\u60f3\u60f3</button>' +
        '<button class="btn-confirm">\u786e\u8ba4\u5220\u9664</button>' +
        '</div>' +
        '</div>';
      document.body.appendChild(modal);
      modal.querySelector('.btn-cancel').addEventListener('click', () => {
        modal.classList.add('hidden');
      });
      modal.querySelector('.btn-confirm').addEventListener('click', () => {
        App.store.clear();
        modal.classList.add('hidden');
        App.toast('\u6570\u636e\u5df2\u6e05\u9664');
        this.refresh();
      });
    }
    modal.classList.remove('hidden');
  }
};

document.addEventListener('DOMContentLoaded', function () {
  Profile.init();
});
