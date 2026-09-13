/* ==================== breathing.js — 478呼吸法 ==================== */

const Breathing = {
  isRunning: false,
  currentRound: 0,
  totalRounds: 4,
  phase: 'idle', // idle, inhale, hold, exhale, rest
  timers: [],   // 所有计时器引用，方便统一清除
  audioCtx: null,
  soundEnabled: true,

  // 清除所有计时器
  clearTimers() {
    this.timers.forEach(t => clearTimeout(t));
    this.timers = [];
  },

  // 添加计时器（统一管理）
  setTimer(fn, ms) {
    const id = setTimeout(() => {
      this.timers = this.timers.filter(t => t !== id);
      fn();
    }, ms);
    this.timers.push(id);
    return id;
  },

  // 初始化音频上下文
  ensureAudio() {
    if (!this.audioCtx) {
      try {
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      } catch (e) {
        this.soundEnabled = false;
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  },

  // 播放提示音
  // type: 'inhale' (升调柔和), 'hold' (低沉单音), 'exhale' (降调柔和), 'done' (完成音阶)
  playTone(type) {
    if (!this.soundEnabled) return;
    this.ensureAudio();
    if (!this.audioCtx) return;

    const ctx = this.audioCtx;
    const now = ctx.currentTime;

    if (type === 'inhale') {
      // 吸气：C5→G5 上升，柔和正弦波
      this._playNote(523.25, 0.15, now, 0.4);
      this._playNote(783.99, 0.15, now + 0.15, 0.4);
    } else if (type === 'hold') {
      // 屏息：低沉单音 E4，持续
      this._playNote(329.63, 0.3, now, 0.5);
    } else if (type === 'exhale') {
      // 呼气：G5→C5 下降
      this._playNote(783.99, 0.15, now, 0.4);
      this._playNote(523.25, 0.15, now + 0.15, 0.4);
    } else if (type === 'rest') {
      // 休息：轻柔叮咚
      this._playNote(659.25, 0.12, now, 0.3);
    } else if (type === 'done') {
      // 完成：C5→E5→G5→C6 琶音
      this._playNote(523.25, 0.15, now, 0.4);
      this._playNote(659.25, 0.15, now + 0.15, 0.4);
      this._playNote(783.99, 0.15, now + 0.3, 0.4);
      this._playNote(1046.5, 0.3, now + 0.45, 0.5);
    }
  },

  _playNote(freq, duration, startTime, volume) {
    const ctx = this.audioCtx;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0, startTime);
    gain.gain.linearRampToValueAtTime(volume, startTime + 0.03);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(startTime);
    osc.stop(startTime + duration + 0.05);
  },

  start() {
    if (this.isRunning) {
      this.stop();
      return;
    }
    this.isRunning = true;
    this.currentRound = 0;
    this.updateButton();
    this.ensureAudio();
    this.nextRound();
  },

  stop() {
    this.isRunning = false;
    this.clearTimers();
    this.phase = 'idle';
    this.currentRound = 0;
    this.resetCircle();
    document.getElementById('breath-text').textContent = '准备';
    document.getElementById('breath-count').textContent = '';
    document.getElementById('breath-round').textContent = '0';
    document.getElementById('breath-phase').textContent = '点击开始';
    this.updateButton();
  },

  nextRound() {
    this.currentRound++;
    if (this.currentRound > this.totalRounds) {
      this.finish();
      return;
    }
    document.getElementById('breath-round').textContent = this.currentRound;
    this.phaseInhale();
  },

  phaseInhale() {
    this.phase = 'inhale';
    const circle = document.getElementById('breath-circle');
    circle.className = 'breath-circle inhale';
    document.getElementById('breath-text').textContent = '吸气';
    document.getElementById('breath-phase').textContent = '缓慢吸气...';
    this.playTone('inhale');
    this.countdown(4, () => this.phaseHold());
  },

  phaseHold() {
    this.phase = 'hold';
    const circle = document.getElementById('breath-circle');
    circle.className = 'breath-circle hold';
    document.getElementById('breath-text').textContent = '屏息';
    document.getElementById('breath-phase').textContent = '保持...';
    this.playTone('hold');
    this.countdown(7, () => this.phaseExhale());
  },

  phaseExhale() {
    this.phase = 'exhale';
    const circle = document.getElementById('breath-circle');
    circle.className = 'breath-circle exhale';
    document.getElementById('breath-text').textContent = '呼气';
    document.getElementById('breath-phase').textContent = '缓缓呼气...';
    this.playTone('exhale');
    this.countdown(8, () => {
      // 一轮结束
      if (this.currentRound < this.totalRounds) {
        this.phase = 'rest';
        document.getElementById('breath-phase').textContent = '休息2秒...';
        this.resetCircle();
        document.getElementById('breath-text').textContent = '放松';
        this.playTone('rest');
        this.setTimer(() => this.nextRound(), 2000);
      } else {
        this.finish();
      }
    });
  },

  // 用 setTimeout 递归实现倒计时（避免 setInterval 堆叠）
  countdown(seconds, callback) {
    const countEl = document.getElementById('breath-count');
    let remaining = seconds;
    countEl.textContent = remaining;

    const tick = () => {
      remaining--;
      if (remaining <= 0) {
        countEl.textContent = '';
        callback();
      } else {
        countEl.textContent = remaining;
        this.setTimer(tick, 1000);
      }
    };

    this.setTimer(tick, 1000);
  },

  resetCircle() {
    const circle = document.getElementById('breath-circle');
    circle.className = 'breath-circle rest';
  },

  finish() {
    this.isRunning = false;
    this.clearTimers();
    this.resetCircle();
    document.getElementById('breath-text').textContent = '完成';
    document.getElementById('breath-count').textContent = '\u2728';
    document.getElementById('breath-phase').textContent = '做得很棒，晚安';
    this.updateButton();
    this.playTone('done');
    App.toast('478呼吸法完成，好梦');
    // 记录使用
    App.store.set('ynhm_last_breathing', App.formatDate(new Date()));
  },

  updateButton() {
    const btn = document.getElementById('breath-start-btn');
    if (this.isRunning) {
      btn.textContent = '停止';
      btn.classList.add('running');
    } else {
      btn.textContent = '开始呼吸';
      btn.classList.remove('running');
    }
  }
};

document.addEventListener('DOMContentLoaded', function () {
  document.getElementById('breath-start-btn').addEventListener('click', () => Breathing.start());
});
