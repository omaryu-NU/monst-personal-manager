import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const ts=require('typescript');
const source=readFileSync(new URL('../src/play-v07.ts',import.meta.url),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const m=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));
const char=(id,race='亜人')=>({id,name:id,race,type:'反射',style:'バランス型'});
const own=(id,fruitSlots)=>({id,characterId:id,fruitSlots});
const members=[{owned:own('1',[{name:'同族の絆・加撃',grade:'特級L'}]),character:char('1')},{owned:own('2',[{name:'同族の絆・加撃',grade:'特級M'},{name:'撃種の絆・加撃',grade:'特級L'}]),character:char('2')}];
test('同種の実は高い方のみ採用、別種類の適用効果は加算',()=>{
 assert.equal(m.partyAttackBonus(members,0).bonus,4500);
 assert.equal(m.partyAttackBonus(members,0).effects.length,2);
});
test('種族不明や異なる撃種は安易に一致とみなさない',()=>{
 const other={owned:own('3',[{name:'撃種の絆・加撃',grade:'特級L'}]),character:{...char('3'),type:'貫通'}};
 assert.equal(m.partyAttackBonus([other,members[0]],1).bonus,3000);
 assert.equal(m.partyAttackBonus([{owned:own('4',[{name:'同族の絆・加撃',grade:'特級L'}]),character:{id:'4'}},{owned:own('5',[]),character:{id:'5'}}],1).bonus,0);
});
test('未対応の等級は計算に勝手に使用しない',()=>{
 assert.equal(m.effectOf({name:'同族の絆・加撃速',grade:'特級M'}),null);
 assert.equal(m.effectOf({name:'同族の絆・加撃',grade:'特L'}).value,3000);
});
test('乗算・無効な入力を検証',()=>{
 assert.equal(m.estimateAttack(30000,2000,3000,{killer:1.5,attribute:1,emblem:1,weakpoint:1,other:1}),52500);
 assert.throws(()=>m.estimateAttack(-1,0,0,{killer:1,attribute:1,emblem:1,weakpoint:1,other:1}));
});
test('累計経験値からの必要周回数',()=>{
 assert.deepEqual(m.requiredRuns(100,401,100),{missing:301,runs:4});
 assert.deepEqual(m.requiredRuns(500,400,100),{missing:0,runs:0});
 assert.throws(()=>m.requiredRuns(0,100,0));
 assert.throws(()=>m.validateRankTable([{rank:1,cumulativeExp:200},{rank:2,cumulativeExp:100}]));
});
test('EX集計は期間とクエストを考慮',()=>{
 const rows=[{date:'2026-11-01',quest:'A',spawned:true},{date:'2026-11-02',quest:'A',spawned:false},{date:'2026-11-03',quest:'B',spawned:true}];
 assert.deepEqual(m.exStats(rows,'2026-11-01','2026-11-02','A'),{runs:2,spawns:1,rate:.5});
 assert.equal(m.exStats([]).rate,0);
});
test('CSV特殊文字と勝率',()=>{
 assert.match(m.exportCsv([['a,b','x"y']]),/"a,b","x""y"/);
 assert.equal(m.playWinRate([{result:'勝利'},{result:'敗北'}]).rate,.5);
});
test('既存のFirestoreセクションとv0.1保存キーを残す',()=>{
 const sync=readFileSync(new URL('../src/sync.ts',import.meta.url),'utf8');
 const persist=readFileSync(new URL('../src/persistence.ts',import.meta.url),'utf8');
 assert.match(sync,/playLogs/);assert.match(sync,/runTransaction/);assert.match(persist,/monst-personal-v1/);
});
test('legacy state stays valid with optional playLogs, no schemaVersion change',()=>{
 const path=new URL('../src/persistence.ts',import.meta.url);
 const persist=readFileSync(path,'utf8');
 const types=readFileSync(new URL('../src/types.ts',import.meta.url),'utf8');
 assert.match(persist,/playLogs:Array\.isArray\(v\.playLogs\)\?v\.playLogs:\[\]/);
 assert.match(types,/schemaVersion: 1/);
 assert.match(types,/playLogs\?: PlayLog\[\]/);
});
