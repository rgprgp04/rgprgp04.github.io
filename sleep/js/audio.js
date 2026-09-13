/* ==================== audio.js — 助眠音库 ==================== */

// 音频数据 — 使用免费公版音频源（后续可替换为自有CDN）
const AUDIO_DATA = [
  { id: 'rain', name: '雨夜窗台', desc: '淅淅沥沥的雨声，最经典的白噪音', tag: 'nature', icon: '\u{1F327}', duration: '循环', color: '#4a90d9' },
  { id: 'forest', name: '深林鸟语', desc: '清晨森林，鸟鸣与微风穿叶', tag: 'nature', icon: '\u{1F333}', duration: '循环', color: '#4ade80' },
  { id: 'ocean', name: '海浪轻拍', desc: '规律的海浪声，天然的摇篮曲', tag: 'nature', icon: '\u{1F30A}', duration: '循环', color: '#3b82f6' },
  { id: 'thunder', name: '远雷低语', desc: '远处雷声隆隆，安全感白噪音', tag: 'nature', icon: '\u{26C8}', duration: '循环', color: '#6366f1' },
  { id: 'fire', name: '篝火噼啪', desc: '木柴燃烧的温暖声响', tag: 'nature', icon: '\u{1F525}', duration: '循环', color: '#f59e0b' },
  { id: 'whitenoise', name: '纯白噪音', desc: '全频段均匀白噪音，屏蔽杂音', tag: 'white', icon: '\u{1F30C}', duration: '循环', color: '#7c5cfc' },
  { id: 'pinknoise', name: '粉红噪音', desc: '低频偏重，比白噪音更柔和', tag: 'white', icon: '\u{1F47C}', duration: '循环', color: '#ec4899' },
  { id: 'brownnoise', name: '棕色噪音', desc: '低沉轰鸣，深度屏蔽型噪音', tag: 'white', icon: '\u{1F7E4}', duration: '循环', color: '#92400e' },
  { id: 'fan', name: '风扇声', desc: '夏日电扇的规律转动声', tag: 'white', icon: '\u{1F9BB}', duration: '循环', color: '#6b7280' },
  { id: 'meditation1', name: '身体扫描引导', desc: '从头到脚放松每一寸肌肉', tag: 'guide', icon: '\u{1F9D8}', duration: '15分钟', color: '#a78bfa' },
  { id: 'meditation2', name: '渐进式放松', desc: '紧绷-释放，让身体学会松弛', tag: 'guide', icon: '\u{1F6AB}', duration: '12分钟', color: '#f0c75e' },
  { id: 'meditation3', name: '正念呼吸', desc: '跟随引导，专注每一次呼吸', tag: 'guide', icon: '\u{1F31F}', duration: '10分钟', color: '#4ade80' }
];

// 用 Web Audio API 生成程序化噪音（无需外部音频文件）
const AudioModule = {
  audioCtx: null,
  currentId: null,
  isPlaying: false,
  currentTab: 'all',
  timerMin: 0,
  timerEnd: 0,
  timerInterval: null,
  noiseNode: null,
  gainNode: null,
  lfo: null,
  filterNode: null,

  init() {
    // 懒加载 AudioContext
  },

  ensureCtx() {
    if (!this.audioCtx) {
      this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  },

  // 生成噪音（white/pink/brown）
  createNoise(type) {
    const ctx = this.audioCtx;
    const bufferSize = 2 * ctx.sampleRate;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);

    if (type === 'white') {
      for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
      }
    } else if (type === 'pink') {
      let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        b0 = 0.99886 * b0 + white * 0.0555179;
        b1 = 0.99332 * b1 + white * 0.0750759;
        b2 = 0.96900 * b2 + white * 0.1538520;
        b3 = 0.86650 * b3 + white * 0.3104856;
        b4 = 0.55000 * b4 + white * 0.5329522;
        b5 = -0.7616 * b5 - white * 0.0168980;
        data[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.11;
        b6 = white * 0.115926;
      }
    } else if (type === 'brown') {
      let lastOut = 0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        data[i] = (lastOut + (0.02 * white)) / 1.02;
        lastOut = data[i];
        data[i] *= 3.5;
      }
    }
    return buffer;
  },

  // 生成雨声（过滤后的噪音+随机脉冲）
  createRainBuffer() {
    const ctx = this.audioCtx;
    const bufferSize = 4 * ctx.sampleRate;
    const buffer = ctx.createBuffer(2, bufferSize, ctx.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const data = buffer.getChannelData(ch);
      let last = 0;
      for (let i = 0; i < bufferSize; i++) {
        // 基础白噪音
        const white = Math.random() * 2 - 1;
        // 低通滤波模拟雨滴
        last = last * 0.98 + white * 0.02;
        data[i] = last * 3;
        // 随机雨滴脉冲
        if (Math.random() < 0.0008) {
          data[i] += (Math.random() - 0.5) * 0.5;
        }
      }
    }
    return buffer;
  },

  // 播放指定音频
  play(id) {
    const item = AUDIO_DATA.find(a => a.id === id);
    if (!item) return;

    this.ensureCtx();
    this.stop();

    this.currentId = id;
    this.isPlaying = true;

    const ctx = this.audioCtx;

    // 创建 gain 节点
    this.gainNode = ctx.createGain();
    this.gainNode.gain.value = 0;
    this.gainNode.connect(ctx.destination);
    // 淡入
    this.gainNode.gain.linearRampToValueAtTime(0.4, ctx.currentTime + 0.5);

    // 根据类型生成音频
    let source;
    if (id === 'whitenoise') {
      source = this.createNoiseSource('white');
    } else if (id === 'pinknoise') {
      source = this.createNoiseSource('pink');
    } else if (id === 'brownnoise') {
      source = this.createNoiseSource('brown');
    } else if (id === 'rain') {
      source = this.createRainSource();
    } else if (id === 'forest') {
      source = this.createForestSource();
    } else if (id === 'ocean') {
      source = this.createOceanSource();
    } else if (id === 'thunder') {
      source = this.createThunderSource();
    } else if (id === 'fire') {
      source = this.createFireSource();
    } else if (id === 'fan') {
      source = this.createFanSource();
    } else if (id.startsWith('meditation')) {
      // 冥想引导 — 用柔和的低频噪音+提示音替代
      source = this.createMeditationSource();
    } else {
      source = this.createNoiseSource('pink');
    }

    this.noiseNode = source;
    // source 在各 create*Source 内部已连接到 gainNode，无需重复连接
    source.start();

    this.updateUI(item);
    this.startProgress();
  },

  createNoiseSource(type) {
    const ctx = this.audioCtx;
    const buffer = this.createNoise(type);
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    src.connect(this.gainNode);
    return src;
  },

  createRainSource() {
    const ctx = this.audioCtx;
    const buffer = this.createRainBuffer();
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    // 加低通滤波
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 2000;
    this.filterNode = filter;
    src.connect(filter);
    filter.connect(this.gainNode);
    return src;
  },

  createForestSource() {
    const ctx = this.audioCtx;
    // 粉红噪音 + 偶发鸟鸣频率
    const buffer = this.createNoise('pink');
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = 3000;
    filter.Q.value = 0.5;
    this.filterNode = filter;
    src.connect(filter);
    filter.connect(this.gainNode);
    // LFO 制造波动
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.3;
    const lfoGain = ctx.createGain();
    lfoGain.gain.value = 500;
    lfo.connect(lfoGain);
    lfoGain.connect(filter.frequency);
    this.lfo = lfo;
    lfo.start();
    return src;
  },

  createOceanSource() {
    const ctx = this.audioCtx;
    const buffer = this.createNoise('brown');
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    // LFO 控制音量模拟海浪起伏
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.12;
    const lfoGain = ctx.createGain();
    lfoGain.gain.value = 0.25;
    const waveGain = ctx.createGain();
    waveGain.gain.value = 0.5;
    lfo.connect(lfoGain);
    lfoGain.connect(waveGain.gain);
    src.connect(waveGain);
    waveGain.connect(this.gainNode);
    this.lfo = lfo;
    lfo.start();
    return src;
  },

  createThunderSource() {
    const ctx = this.audioCtx;
    const buffer = this.createNoise('brown');
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 200;
    this.filterNode = filter;
    src.connect(filter);
    filter.connect(this.gainNode);
    // 低频脉冲模拟雷声
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.08;
    const lfoGain = ctx.createGain();
    lfoGain.gain.value = 0.3;
    lfo.connect(lfoGain);
    lfoGain.connect(this.gainNode.gain);
    this.lfo = lfo;
    lfo.start();
    return src;
  },

  createFireSource() {
    const ctx = this.audioCtx;
    const bufferSize = 4 * ctx.sampleRate;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      const white = Math.random() * 2 - 1;
      data[i] = white * 0.05;
      if (Math.random() < 0.002) {
        data[i] += (Math.random() - 0.5) * 0.8;
      }
    }
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 1000;
    this.filterNode = filter;
    src.connect(filter);
    filter.connect(this.gainNode);
    return src;
  },

  createFanSource() {
    const ctx = this.audioCtx;
    const buffer = this.createNoise('white');
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = 400;
    filter.Q.value = 1;
    this.filterNode = filter;
    src.connect(filter);
    filter.connect(this.gainNode);
    // LFO 模拟风扇转动
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 2;
    const lfoGain = ctx.createGain();
    lfoGain.gain.value = 100;
    lfo.connect(lfoGain);
    lfoGain.connect(filter.frequency);
    this.lfo = lfo;
    lfo.start();
    return src;
  },

  createMeditationSource() {
    const ctx = this.audioCtx;
    // 低频持续音 + 粉红噪音
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = 136.1; // OM 频率
    const oscGain = ctx.createGain();
    oscGain.gain.value = 0.08;
    osc.connect(oscGain);
    oscGain.connect(this.gainNode);
    // 同时叠粉红噪音
    const buffer = this.createNoise('pink');
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    const noiseGain = ctx.createGain();
    noiseGain.gain.value = 0.1;
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 800;
    src.connect(filter);
    filter.connect(noiseGain);
    noiseGain.connect(this.gainNode);
    // 返回一个虚拟 source（实际控制用 osc）
    this._meditationOsc = osc;
    osc.start();
    return src;
  },

  stop() {
    // 捕获当前节点引用，避免 setTimeout 回调误停新节点
    const oldNoise = this.noiseNode;
    const oldOsc = this._meditationOsc;
    const oldLfo = this.lfo;
    const oldFilter = this.filterNode;
    const oldGain = this.gainNode;

    // 立即清空引用，让 play() 可以安全赋新值
    this.noiseNode = null;
    this._meditationOsc = null;
    this.lfo = null;
    this.filterNode = null;
    this.gainNode = null;

    // 淡出
    if (oldGain && this.audioCtx) {
      try {
        oldGain.gain.linearRampToValueAtTime(0, this.audioCtx.currentTime + 0.3);
      } catch (e) {}
    }

    // 延迟停止旧节点
    setTimeout(() => {
      if (oldNoise) { try { oldNoise.stop(); } catch (e) {} }
      if (oldOsc) { try { oldOsc.stop(); } catch (e) {} }
      if (oldLfo) { try { oldLfo.stop(); } catch (e) {} }
      if (oldFilter) { try { oldFilter.disconnect(); } catch (e) {} }
      if (oldGain) { try { oldGain.disconnect(); } catch (e) {} }
    }, 350);

    this.isPlaying = false;
    this.stopProgress();
    this.updateUI(null);
    this.stopTimer();
  },

  togglePlay() {
    if (this.isPlaying) {
      this.stop();
    } else if (this.currentId) {
      this.play(this.currentId);
    }
  },

  // 按标签快速播放（首页快捷按钮）
  playByTag(tag) {
    const item = AUDIO_DATA.find(a => a.id === tag || a.tag === tag);
    if (item) {
      this.play(item.id);
    }
  },

  // 下一首
  playNext() {
    const idx = AUDIO_DATA.findIndex(a => a.id === this.currentId);
    const next = AUDIO_DATA[(idx + 1) % AUDIO_DATA.length];
    this.play(next.id);
  },

  playPrev() {
    const idx = AUDIO_DATA.findIndex(a => a.id === this.currentId);
    const prev = AUDIO_DATA[(idx - 1 + AUDIO_DATA.length) % AUDIO_DATA.length];
    this.play(prev.id);
  },

  // 进度模拟（循环音频无真实进度，用时间显示）
  startProgress() {
    this._playStart = Date.now();
    this._progressTimer = setInterval(() => {
      if (!this.isPlaying) return;
      const elapsed = Math.floor((Date.now() - this._playStart) / 1000);
      const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
      const ss = String(elapsed % 60).padStart(2, '0');
      const timeEl = document.getElementById('player-time');
      if (timeEl) timeEl.textContent = mm + ':' + ss;
      // 进度条缓慢推进（循环动画）
      const fill = document.getElementById('player-progress-fill');
      if (fill) {
        const pct = ((elapsed % 60) / 60) * 100;
        fill.style.width = pct + '%';
      }
    }, 500);
  },

  stopProgress() {
    clearInterval(this._progressTimer);
  },

  // 更新播放栏 UI
  updateUI(item) {
    const bar = document.getElementById('audio-player-bar');
    const playBtn = document.getElementById('player-play');
    const titleEl = document.getElementById('player-title');

    if (item) {
      bar.classList.remove('hidden');
      titleEl.textContent = item.name;
      playBtn.classList.add('playing');
    } else {
      playBtn.classList.remove('playing');
    }

    // 更新列表高亮
    document.querySelectorAll('.audio-card').forEach(card => {
      card.classList.toggle('playing', card.dataset.id === this.currentId && this.isPlaying);
    });
  },

  // 定时关闭
  setTimer(min) {
    this.stopTimer();
    if (min > 0) {
      this.timerMin = min;
      this.timerEnd = Date.now() + min * 60 * 1000;
      this.timerInterval = setInterval(() => {
        const remain = Math.floor((this.timerEnd - Date.now()) / 1000);
        if (remain <= 0) {
          this.stop();
          App.toast('定时关闭，晚安');
          return;
        }
      }, 1000);
      document.getElementById('player-timer').classList.add('active');
      App.toast('已设定 ' + min + ' 分钟后关闭');
    } else {
      document.getElementById('player-timer').classList.remove('active');
      App.toast('已取消定时');
    }
  },

  stopTimer() {
    clearInterval(this.timerInterval);
    this.timerMin = 0;
    const tBtn = document.getElementById('player-timer');
    if (tBtn) tBtn.classList.remove('active');
  },

  // 渲染列表
  refreshList() {
    const list = document.getElementById('audio-list');
    if (!list) return;
    list.innerHTML = '';

    const filtered = this.currentTab === 'all'
      ? AUDIO_DATA
      : AUDIO_DATA.filter(a => a.tag === this.currentTab);

    filtered.forEach(item => {
      const card = document.createElement('div');
      card.className = 'audio-card';
      card.dataset.id = item.id;
      if (this.currentId === item.id && this.isPlaying) card.classList.add('playing');
      card.innerHTML =
        '<div class="audio-cover" style="background:' + item.color + '22">' + item.icon + '</div>' +
        '<div class="audio-info">' +
        '<div class="audio-name">' + item.name + '</div>' +
        '<div class="audio-desc">' + item.desc + '</div>' +
        '</div>' +
        '<div class="audio-duration">' + item.duration + '</div>';
      card.addEventListener('click', () => {
        if (this.currentId === item.id && this.isPlaying) {
          this.stop();
        } else {
          this.play(item.id);
        }
      });
      list.appendChild(card);
    });
  },

  // 绑定事件
  bindEvents() {
    // Tab 切换
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentTab = btn.dataset.tab;
        this.refreshList();
      });
    });

    // 播放控制
    document.getElementById('player-play').addEventListener('click', () => this.togglePlay());
    document.getElementById('player-next').addEventListener('click', () => this.playNext());
    document.getElementById('player-prev').addEventListener('click', () => this.playPrev());

    // 定时弹窗
    document.getElementById('player-timer').addEventListener('click', () => {
      document.getElementById('timer-popup').classList.toggle('hidden');
    });
    document.querySelectorAll('.timer-options button').forEach(btn => {
      btn.addEventListener('click', () => {
        const min = parseInt(btn.dataset.min);
        this.setTimer(min);
        document.getElementById('timer-popup').classList.add('hidden');
      });
    });
  }
};

document.addEventListener('DOMContentLoaded', function () {
  AudioModule.bindEvents();
  AudioModule.refreshList();
});
