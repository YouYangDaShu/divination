#!/usr/bin/env node
/**
 * iztro 桥接脚本
 * 用法: node ziwei_bridge.js <solarDate> <timeIndex> <gender>
 * 输出: JSON (iztro 原始结果，精简+重排)
 */
const { astro } = require('iztro');

const [,, solarDate, timeIndexStr, gender] = process.argv;
if (!solarDate || !timeIndexStr || !gender) {
  console.error('Usage: node ziwei_bridge.js <YYYY-MM-DD> <timeIndex 0-11> <男|女>');
  process.exit(1);
}

const timeIndex = parseInt(timeIndexStr, 10);
if (isNaN(timeIndex) || timeIndex < 0 || timeIndex > 11) {
  console.error('timeIndex must be 0-11 (0=子,1=丑,...,11=亥)');
  process.exit(1);
}

try {
  const result = astro.bySolar(solarDate, timeIndex, gender);

  // 精简输出：去掉函数类型的属性
  const cleanPalaces = result.palaces.map(p => ({
    index: p.index,
    name: p.name,
    isBodyPalace: p.isBodyPalace,
    isOriginalPalace: p.isOriginalPalace,
    heavenlyStem: p.heavenlyStem,
    earthlyBranch: p.earthlyBranch,
    majorStars: (p.majorStars || []).map(s => ({
      name: s.name,
      brightness: s.brightness || '',
      mutagen: s.mutagen ? '化' + s.mutagen : '',
    })),
    minorStars: (p.minorStars || []).map(s => ({
      name: s.name,
      brightness: s.brightness || '',
    })),
    adjectiveStars: (p.adjectiveStars || []).map(s => ({
      name: s.name,
    })),
    changsheng12: p.changsheng12 || '',
    boshi12: p.boshi12 || '',
    jiangqian12: p.jiangqian12 || '',
    suiqian12: p.suiqian12 || '',
    decadal: p.decadal || null,
    ages: p.ages || null,
  }));

  // 矫正 isOriginalPalace：iztro 有时标记不准，按 name 矫正
  const realMingIdx = cleanPalaces.findIndex(p => p.name === '命宫');
  cleanPalaces.forEach((p, i) => { p.isOriginalPalace = (i === realMingIdx); });

  // 矫正 isBodyPalace：用 earthlyBranchOfBodyPalace 匹配
  const bodyBranch = result.earthlyBranchOfBodyPalace;
  cleanPalaces.forEach(p => { p.isBodyPalace = (p.earthlyBranch === bodyBranch); });

  // 重排：从命宫开始，按传统顺序 命宫→父母→福德→...
  const mingIdx = cleanPalaces.findIndex(p => p.name === '命宫');
  if (mingIdx > 0) {
    const reordered = [];
    for (let i = 0; i < 12; i++) {
      reordered.push(cleanPalaces[(mingIdx + i) % 12]);
    }
    reordered.forEach((p, i) => { p.index = i; });
    result.palaces = reordered;
  } else {
    result.palaces = cleanPalaces;
  }

  // 替换 palaces 为精简版
  if (mingIdx <= 0) {
    result.palaces = cleanPalaces;
  }

  const output = {
    gender: result.gender,
    solarDate: result.solarDate,
    lunarDate: result.lunarDate,
    chineseDate: result.chineseDate,
    rawDates: result.rawDates,
    time: result.time,
    timeRange: result.timeRange,
    sign: result.sign,
    zodiac: result.zodiac,
    soul: result.soul,
    body: result.body,
    fiveElementsClass: result.fiveElementsClass,
    earthlyBranchOfSoulPalace: result.earthlyBranchOfSoulPalace,
    earthlyBranchOfBodyPalace: result.earthlyBranchOfBodyPalace,
    palaces: result.palaces,
  };

  console.log(JSON.stringify(output));
} catch (e) {
  console.error('iztro error:', e.message);
  process.exit(1);
}
