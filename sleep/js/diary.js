/* ==================== diary.js — 睡眠日记 ==================== */

const Diary = {
  records: [],
  rating: 0,

  init() {
    this.records = App.store.get('ynhm_diary', []);
    this.bindEvents();
    this.refresh();
  },

  bindEvents() {
    // 星级评分
    document.querySelectorAll('#diary-rating .star').forEach(star => {
      star.addEventListener('click', () => {
        this.rating = parseInt(star.dataset.score);
        this.updateStars();
      });
    });

    // 保存
    document.getElementById('diary-save-btn').addEventListener('click', () => this.save());
  },

  updateStars() {
    document.querySelectorAll('#diary-rating .star').forEach(star => {
      const score = parseInt(star.dataset.score);
      star.classList.toggle('active', score <= this.rating);
      star.textContent = score <= this.rating ? '\u2605' : '\u2606';
    });
  },

  save() {
    const bedtime = document.getElementById('diary-bedtime').value;
    const waketime = document.getElementById('diary-waketime').value;
    const note = document.getElementById('diary-note').value;

    if (!bedtime || !waketime) {
      App.toast('请填写入睡和醒来时间');
      return;
    }
    if (this.rating === 0) {
      App.toast('请选择睡眠质量');
      return;
    }

    // 计算睡眠时长
    const duration = this.calcDuration(bedtime, waketime);

    const record = {
      id: Date.now(),
      date: App.formatDate(new Date()),
      bedtime: bedtime,
      waketime: waketime,
      duration: duration,
      rating: this.rating,
      note: note || ''
    };

    this.records.unshift(record);
    App.store.set('ynhm_diary', this.records);

    // 重置表单
    document.getElementById('diary-bedtime').value = '';
    document.getElementById('diary-waketime').value = '';
    document.getElementById('diary-note').value = '';
    this.rating = 0;
    this.updateStars();

    App.toast('记录已保存');
    this.refresh();
  },

  calcDuration(bedtime, waketime) {
    const [bh, bm] = bedtime.split(':').map(Number);
    const [wh, wm] = waketime.split(':').map(Number);
    let mins = (wh * 60 + wm) - (bh * 60 + bm);
    if (mins < 0) mins += 24 * 60; // 跨天
    return mins;
  },

  formatDuration(mins) {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return h + '小时' + (m > 0 ? m + '分' : '');
  },

  delete(id) {
    this.records = this.records.filter(r => r.id !== id);
    App.store.set('ynhm_diary', this.records);
    App.toast('已删除');
    this.refresh();
  },

  refresh() {
    this.records = App.store.get('ynhm_diary', []);
    this.renderStats();
    this.renderList();
  },

  renderStats() {
    const statsEl = document.getElementById('diary-stats');
    if (this.records.length === 0) {
      statsEl.innerHTML = '';
      return;
    }

    const avgDuration = this.records.reduce((s, r) => s + r.duration, 0) / this.records.length;
    const avgRating = this.records.reduce((s, r) => s + r.rating, 0) / this.records.length;
    const totalDays = new Set(this.records.map(r => r.date)).size;

    statsEl.innerHTML =
      '<div class="stat-card"><div class="stat-value">' + this.formatDuration(Math.round(avgDuration)) + '</div><div class="stat-label">平均睡眠</div></div>' +
      '<div class="stat-card"><div class="stat-value">' + avgRating.toFixed(1) + '</div><div class="stat-label">平均评分</div></div>' +
      '<div class="stat-card"><div class="stat-value">' + totalDays + '</div><div class="stat-label">记录天数</div></div>';
  },

  renderList() {
    const listEl = document.getElementById('diary-list');
    if (this.records.length === 0) {
      listEl.innerHTML = '<div class="diary-empty">还没有记录，今晚来写下第一条吧</div>';
      return;
    }

    listEl.innerHTML = '';
    this.records.forEach(r => {
      const d = new Date(r.date);
      const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
      const stars = '\u2605'.repeat(r.rating) + '\u2606'.repeat(5 - r.rating);

      const item = document.createElement('div');
      item.className = 'diary-item';
      item.innerHTML =
        '<div class="diary-date">' +
        '<div class="diary-date-day">' + d.getDate() + '</div>' +
        '<div class="diary-date-month">' + monthNames[d.getMonth()] + '</div>' +
        '</div>' +
        '<div class="diary-detail">' +
        '<div class="diary-time-row">' + r.bedtime + ' <span class="arrow">\u2192</span> ' + r.waketime + '</div>' +
        '<div class="diary-duration">' + this.formatDuration(r.duration) + ' \u00B7 <span class="diary-quality">' + stars + '</span></div>' +
        (r.note ? '<div class="diary-note">' + r.note + '</div>' : '') +
        '</div>' +
        '<button class="diary-delete" data-id="' + r.id + '">\u2717</button>';

      item.querySelector('.diary-delete').addEventListener('click', (e) => {
        e.stopPropagation();
        this.delete(r.id);
      });

      listEl.appendChild(item);
    });
  }
};

document.addEventListener('DOMContentLoaded', function () {
  Diary.init();
});
