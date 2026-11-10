import type { AppState, Character, OwnedCharacter, ExRun, PlayLog } from './types';
import { fruitProgress, normalizeOwned } from './owned-v05';

export type Period = {start?: string; end?:string};
export type Breakdown = {label:string; count:number}[];
export type Rate = {numerator:number; denominator:number; rate:number|null};
export type Daily = {date:string; runs:number; spawns:number; games:number; wins:number};
export const ratio = (numerator:number,denominator:number):Rate=>({numerator,denominator,rate:denominator?numerator/denominator:null});
export function validDate(s:string){return /^\d{4}-\d{2}-\d{2}$/.test(s)&&!Number.isNaN(new Date(s+'T00:00:00Z').getTime())&&new Date(s+'T00:00:00Z').toISOString().slice(0,10)===s;}
export function inPeriod(date:string,period:Period){
 const d=date.slice(0,10);
 return validDate(d)&&(!period.start||d>=period.start)&&(!period.end||d<=period.end);
}
export const accountRows = <T extends {accountId:string}>(rows:T[],accountIds:string[])=>rows.filter(r=>accountIds.includes(r.accountId));
export function breakdown(owned:OwnedCharacter[],catalog:Character[],key:'attribute'|'type'|'style'|'rarity'):Breakdown{
 const map=new Map(catalog.map(c=>[c.id,c]));const counts=new Map<string,number>();
 for(const o of owned){const c=map.get(o.characterId);const v=c?.[key];const label=v===undefined||v===null||v===''?'未登録':String(v);counts.set(label,(counts.get(label)??0)+1);}
 return [...counts].map(([label,count])=>({label,count})).sort((a,b)=>b.count-a.count||a.label.localeCompare(b.label,'ja'));
}
export function ownership(owned:OwnedCharacter[],catalog:Character[]){
 const known=new Set(catalog.map(c=>c.id));const distinct=new Set(owned.map(o=>o.characterId));
 const ownedKnown=[...distinct].filter(id=>known.has(id)).length;
 return {individuals:owned.length,varieties:distinct.size,knownVarieties:ownedKnown,unknownVarieties:distinct.size-ownedKnown,catalogSize:known.size,coverage:ratio(ownedKnown,known.size)};
}
export function fruitSummary(owned:OwnedCharacter[]){
 let complete=0,incomplete=0,unset=0;
 for(const o of owned){const x=normalizeOwned(o);const goals=(x.fruitTargets??[]).filter(f=>f.name&&f.name!=='未設定');
  if(!goals.length){unset++;continue;}
  if(fruitProgress(x).complete)complete++;else incomplete++;
 }
 return {complete,incomplete,unset,goalSet:complete+incomplete,rate:ratio(complete,complete+incomplete)};
}
export function trainingSummary(owned:OwnedCharacter[],todos:{done:boolean}[]){
 const statuses=new Map<string,number>();let luckTotal=0,levelTotal=0,luckKnown=0,levelKnown=0;
 for(const o of owned){const status=o.trainingStatus||'未設定';statuses.set(status,(statuses.get(status)||0)+1);
  if(Number.isFinite(o.luck)){luckTotal+=o.luck;luckKnown++;}if(Number.isFinite(o.level)){levelTotal+=o.level;levelKnown++;}}
 return {statuses:[...statuses].map(([label,count])=>({label,count})),avgLuck:luckKnown?luckTotal/luckKnown:null,avgLevel:levelKnown?levelTotal/levelKnown:null,todoDone:todos.filter(t=>t.done).length,todoTotal:todos.length,todoRate:ratio(todos.filter(t=>t.done).length,todos.length)};
}
export function exAnalysis(runs:ExRun[],period:Period){
 const rows=runs.filter(r=>inPeriod(r.date,period));const spawns=rows.filter(r=>r.spawned).length;
 const byQuest=[...new Set(rows.map(r=>r.quest))].map(quest=>{const part=rows.filter(r=>r.quest===quest);return {quest,...ratio(part.filter(r=>r.spawned).length,part.length)};}).sort((a,b)=>b.denominator-a.denominator);
 return {runs:rows.length,spawns,rate:ratio(spawns,rows.length),byQuest};
}
export function playAnalysis(logs:PlayLog[],period:Period){
 const rows=logs.filter(r=>inPeriod(r.date,period));const wins=rows.filter(r=>r.result==='勝利').length;
 const byQuest=[...new Set(rows.map(r=>r.quest))].map(quest=>{const part=rows.filter(r=>r.quest===quest);return {quest,...ratio(part.filter(r=>r.result==='勝利').length,part.length)};}).sort((a,b)=>b.denominator-a.denominator);
 const byTeam=[...new Set(rows.map(r=>r.teamId).filter((v):v is string=>!!v))].map(teamId=>({teamId,count:rows.filter(r=>r.teamId===teamId).length})).sort((a,b)=>b.count-a.count);
 return {games:rows.length,wins,rate:ratio(wins,rows.length),byQuest,byTeam};
}
export function dailySeries(runs:ExRun[],logs:PlayLog[],period:Period):Daily[]{
 const byDay=new Map<string,Daily>();const get=(d:string)=>{let item=byDay.get(d);if(!item){item={date:d,runs:0,spawns:0,games:0,wins:0};byDay.set(d,item);}return item;};
 for(const r of runs){if(!inPeriod(r.date,period))continue;const v=get(r.date.slice(0,10));v.runs++;if(r.spawned)v.spawns++;}
 for(const p of logs){if(!inPeriod(p.date,period))continue;const v=get(p.date.slice(0,10));v.games++;if(p.result==='勝利')v.wins++;}
 return [...byDay.values()].sort((a,b)=>a.date.localeCompare(b.date));
}
export function accountComparison(state:AppState,first:string,second:string){
 const a=state.owned.filter(o=>o.accountId===first),b=state.owned.filter(o=>o.accountId===second);
 const aa=new Set(a.map(o=>o.characterId)),bb=new Set(b.map(o=>o.characterId));
 return {first:{...ownership(a,state.catalog),fruit:fruitSummary(a)},second:{...ownership(b,state.catalog),fruit:fruitSummary(b)},common:[...aa].filter(id=>bb.has(id)).sort(),firstOnly:[...aa].filter(id=>!bb.has(id)).sort(),secondOnly:[...bb].filter(id=>!aa.has(id)).sort()};
}
export function bondSummary(bonds:{progress:number;history?:{id:string;at:string;progress:number}[]}[]){
 return {friends:bonds.length,historyEntries:bonds.reduce((n,b)=>n+(b.history?.length??0),0),averageProgress:bonds.length?bonds.reduce((n,b)=>n+(Number.isFinite(b.progress)?b.progress:0),0)/bonds.length:null};
}
export function analyticsData(state:AppState,accountIds:string[],period:Period){
 const owned=accountRows(state.owned,accountIds),todos=accountRows(state.todos,accountIds),runs=accountRows(state.runs,accountIds),logs=accountRows(state.playLogs??[],accountIds),bonds=accountRows(state.bonds,accountIds);
 return {owned,ownership:ownership(owned,state.catalog),attributes:breakdown(owned,state.catalog,'attribute'),types:breakdown(owned,state.catalog,'type'),styles:breakdown(owned,state.catalog,'style'),rarities:breakdown(owned,state.catalog,'rarity'),fruit:fruitSummary(owned),training:trainingSummary(owned,todos),ex:exAnalysis(runs,period),play:playAnalysis(logs,period),bonds:bondSummary(bonds),daily:dailySeries(runs,logs,period),todoCount:todos.length};
}
export function csvRows(rows:(string|number|null|undefined)[][]){return '\uFEFF'+rows.map(row=>row.map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(',')).join('\r\n');}
export function analyticsCsv(state:AppState,accountIds:string[],period:Period){
 const d=analyticsData(state,accountIds,period);
 const result:(string|number|null|undefined)[][]=[['区分','項目','値'],['図鑑','所持個体数',d.ownership.individuals],['図鑑','所持種類数',d.ownership.varieties],['図鑑','図鑑収録種類数',d.ownership.catalogSize],['図鑑','図鑑所持率',d.ownership.coverage.rate],['厳選','完了',d.fruit.complete],['厳選','未完了',d.fruit.incomplete],['厳選','目標未設定',d.fruit.unset],['EX','周回数',d.ex.runs],['EX','出現数',d.ex.spawns],['EX','観測出現率',d.ex.rate.rate],['プレイ','勝利',d.play.wins],['プレイ','記録件数',d.play.games],['プレイ','観測勝率',d.play.rate.rate]];
 for(const r of d.attributes)result.push(['属性',r.label,r.count]);
 for(const r of d.daily)result.push(['日別EX周回',r.date,r.runs],['日別EX出現',r.date,r.spawns],['日別プレイ',r.date,r.games],['日別勝利',r.date,r.wins]);
 return csvRows(result);
}
