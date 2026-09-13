/* ==================== science.js — 睡眠科普 ==================== */

const SCIENCE_DATA = [
  {
    icon: '\u{1F4A1}',
    tag: 'fact',
    tagText: '冷知识',
    title: '人类一生花1/3时间睡觉',
    content: '<p>按平均寿命78岁计算，人一生大约要睡26年。其中约6年在做梦，约2年在辗转反侧。</p><p>睡眠不是"浪费时间"，而是大脑的夜间维护期——清除代谢废物、巩固记忆、修复免疫系统。</p><div class="tip">如果觉得睡觉浪费时间，想想你不舍得保养的那台车</div>'
  },
  {
    icon: '\u{1F319}',
    tag: 'myth',
    tagText: '误区',
    title: '喝酒助眠？其实适得其反',
    content: '<p>酒精确实能让你更快入睡，但它会破坏下半夜的REM睡眠，导致浅睡增多、深睡减少。</p><p>结果就是：睡得早、醒得早、第二天更累。长期用酒"助眠"还会产生依赖。</p><div class="tip">想喝杯热的？温牛奶或甘菊茶比酒靠谱多了</div>'
  },
  {
    icon: '\u{1F4A8}',
    tag: 'fact',
    tagText: '科学',
    title: '478呼吸法的原理',
    content: '<p>478呼吸法由哈佛医学院安德鲁·韦尔博士提出，核心是激活副交感神经系统（"休息与消化"模式）。</p><p>吸气4秒\u2192充分供氧；屏息7秒\u2192让氧气在血液中交换；呼气8秒\u2192排出二氧化碳、降低心率。</p><p>4秒+7秒+8秒=19秒，4轮约76秒，不到1分半就能让心率显著下降。</p><div class="tip">练习越多越有效，第一周可能觉得数秒数很累</div>'
  },
  {
    icon: '\u{1F9CA}',
    tag: 'fact',
    tagText: '冷知识',
    title: '你的大脑在睡觉时"洗澡"',
    content: '<p>2013年罗切斯特大学发现，睡眠时大脑的"类淋巴系统"会扩张约60%，脑脊液冲刷神经细胞间隙，清除清醒时积累的代谢废物（包括与阿尔茨海默症相关的淀粉样蛋白）。</p><p>简单说：不睡觉=大脑没洗澡，长期不睡=垃圾堆积。</p><div class="tip">熬一次夜，大脑要"加班"好几天才能清理完</div>'
  },
  {
    icon: '\u{23F0}',
    tag: 'myth',
    tagText: '误区',
    title: '周末补觉能还"睡眠债"？',
    content: '<p>研究表明，周末多睡2-3小时只能部分恢复认知功能，无法弥补深睡不足对代谢和免疫的损害。</p><p>更糟的是，周末晚睡晚起会打乱生物钟，让周一更难起床——这叫"社交时差"。</p><div class="tip">保持每天固定作息比周末"还债"有效100倍</div>'
  },
  {
    icon: '\u{1F4C9}',
    tag: 'fact',
    tagText: '数据',
    title: '入睡快≠睡眠好',
    content: '<p>躺下5分钟就睡着，看似效率高，实际上是睡眠不足的信号——正常人需要10-20分钟入睡。</p><p>入睡太快说明你的"睡眠压力"已经很高，大脑在"催债"。</p><p>反过来说，躺20分钟没睡着也是正常的，别焦虑。</p><div class="tip">15分钟入睡是黄金标准，太快太慢都需要注意</div>'
  },
  {
    icon: '\u{1F6CF}',
    tag: 'tip-tag',
    tagText: '技巧',
    title: '最佳睡姿是哪一种？',
    content: '<p>侧卧（尤其左侧）适合大多数人，能减少胃酸反流、缓解打鼾。</p><p>仰卧适合颈椎不好的人，但容易打鼾。趴卧最不推荐，会压迫颈椎和胸腔。</p><p>胎儿式（蜷缩侧卧）是最自然的睡姿，胎儿在子宫里就是这个姿势。</p><div class="tip">膝盖间夹个枕头能减少侧卧时腰部压力</div>'
  },
  {
    icon: '\u{1F4A7}',
    tag: 'tip-tag',
    tagText: '技巧',
    title: '睡前喝水有讲究',
    content: '<p>睡前1小时喝半杯温水（约100ml）有助于夜间血液循环，但不要喝太多——起夜会打断深睡。</p><p>避免在睡前喝含咖啡因的饮料（咖啡、茶、可乐、功能饮料），咖啡因的半衰期约6小时。</p><p>酒虽然利尿催眠但破坏睡眠结构，能不喝就不喝。</p><div class="tip">放杯水在床头，醒来时小口润唇即可</div>'
  },
  {
    icon: '\u{1F321}',
    tag: 'fact',
    tagText: '科学',
    title: '为什么18-22度最好睡',
    content: '<p>入睡时核心体温需要下降约0.5度，凉爽的环境帮助散热，加速入睡。</p><p>超过24度会让人频繁醒来，低于16度则可能因寒冷醒来。</p><p>这也是泡脚助眠的原因：脚部血管扩张散热\u2192核心体温下降\u2192困意来袭。</p><div class="tip">怕冷就盖被子，别把室温调太高</div>'
  }
];

const Science = {
  init() {
    this.render();
  },

  render() {
    const listEl = document.getElementById('science-list');
    if (!listEl) return;
    listEl.innerHTML = '';

    SCIENCE_DATA.forEach((item, idx) => {
      const card = document.createElement('div');
      card.className = 'science-card';
      card.innerHTML =
        '<div class="science-card-header">' +
        '<div class="science-card-icon" style="background:' + this.getTagColor(item.tag) + '22">' + item.icon + '</div>' +
        '<div class="science-card-title">' + item.title + '</div>' +
        '<span class="science-card-arrow">\u25BC</span>' +
        '</div>' +
        '<div class="science-card-body">' +
        '<div class="science-card-content">' +
        '<span class="science-tag ' + item.tag + '">' + item.tagText + '</span>' +
        item.content +
        '</div>' +
        '</div>';

      card.querySelector('.science-card-header').addEventListener('click', () => {
        card.classList.toggle('expanded');
      });

      listEl.appendChild(card);
    });
  },

  getTagColor(tag) {
    const colors = {
      fact: '#7c5cfc',
      myth: '#e8505e',
      'tip-tag': '#f0c75e'
    };
    return colors[tag] || '#7c5cfc';
  },

  refresh() {
    // 已渲染，无需重复
  }
};

document.addEventListener('DOMContentLoaded', function () {
  Science.init();
});
