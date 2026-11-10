import type { AppState, Character, OwnedCharacter, FruitSlot, ExRun, Bond, PlayLog } from './types';

export type FruitEffect = { name:string; grade:string; scope:'race'|'type'|'style'; value:number; source:string };
const gradeMap:Record<string,number[]>={
 '同族の絆・加撃':[500,750,1000,2000,2500,3000,3300],
 '撃種の絆・加撃':[250,375,500,1000,1250,1500,1650],
 '戦型の絆・加撃':[250,375,500,1000,1250,1500,1650],
 '同族の絆・加撃速':[0,0,0,0,0,2000,2200],
 '同族の絆・加命撃':[0,0,0,0,0,2000,2200],
 '撃種の絆・加撃速':[0,0,0,0,0,1000,1100],
 '撃種の絆・加命撃':[0,0,0,0,0,1000,1100],
 '戦型の絆・加撃速':[0,0,0,0,0,1000,1100],
 '戦型の絆・加命撃':[0,0,0,0,0,1000,1100]
};
const grades=['1級','1級M','1級L','特級','特級M','特級L','特級EL'];
const gradeAlias:Record<string,string>={'特L':'特級L','特M':'特級M','特EL':'特級EL'};
const SOURCE='https://appmedia.jp/monst/2177008';
export function effectOf(slot:FruitSlot):FruitEffect|null {
 const name=slot.name.trim();const grade=gradeAlias[slot.grade]??slot.grade;
 const values=gradeMap[name];const i=grades.indexOf(grade);
 if(!values||i<0||!values[i])return null;
 return {name,grade,scope:name.startsWith('同族')?'race':name.startsWith('撃種')?'type':'style',value:values[i],source:SOURCE};
}
export type PartyMember={owned:OwnedCharacter;character:Character};
export function partyAttackBonus(members:PartyMember[],targetIndex:number){
 const target=members[targetIndex];if(!target)return {bonus:0,effects:[] as FruitEffect[],unresolved:[] as string[]};
 const effective=new Map<string,FruitEffect>();const unresolved:string[]=[];
 for(const member of members){
  for(const slot of member.owned.fruitSlots??[]){
   if(!slot.name||slot.name==='未設定')continue;
   const effect=effectOf(slot);
   if(!effect){unresolved.push(`${member.character.name}: ${slot.name} ${slot.grade}`);continue;}
   const memberType=effect.scope==='race'?member.character.race:effect.scope==='type'?member.character.type:member.character.style;
   const targetType=effect.scope==='race'?target.character.race:effect.scope==='type'?target.character.type:target.character.style;
   // Unknown races/hit types MUST NOT match each other.
   if(!memberType||!targetType||memberType!==targetType)continue;
   const key=`${effect.scope}:${memberType}:${effect.name}`;
   if(!effective.has(key)||effective.get(key)!.value<effect.value)effective.set(key,effect);
  }
 }
 const effects=[...effective.values()];return {bonus:effects.reduce((s,e)=>s+e.value,0),effects,unresolved};
}
export function estimateAttack(base:number,plus:number,fruitBonus:number,multipliers:{killer:number;attribute:number;emblem:number;weakpoint:number;other:number}){
 const nums=[base,plus,fruitBonus,...Object.values(multipliers)];
 if(nums.some(n=>!Number.isFinite(n)||n<0))throw Error('0以上の有限数を指定してください');
 return (base+plus+fruitBonus)*Object.values(multipliers).reduce((a,b)=>a*b,1);
}
export function requiredRuns(current:number,goal:number,gain:number){
 if([current,goal,gain].some(n=>!Number.isFinite(n)||n<0)||gain<=0)throw Error('経験値と1周の獲得量を確認してください');
 const missing=Math.max(0,goal-current);return {missing,runs:Math.ceil(missing/gain)};
}
export type RankRow={rank:number;cumulativeExp:number};
export function validateRankTable(input:unknown):RankRow[]{
 if(!Array.isArray(input)||!input.length)throw Error('ランク経験値表の配列が必要です');
 const rows=input.map(x=>({rank:Number(x?.rank),cumulativeExp:Number(x?.cumulativeExp)}));
 if(rows.some(r=>!Number.isInteger(r.rank)||r.rank<1||!Number.isFinite(r.cumulativeExp)||r.cumulativeExp<0))throw Error('ランク表の値が不正です');
 const sorted=[...rows].sort((a,b)=>a.rank-b.rank);
 if(sorted.some((r,i)=>i>0&&(r.rank===sorted[i-1].rank||r.cumulativeExp<sorted[i-1].cumulativeExp)))throw Error('重複ランク・経験値の逆転があります');
 return sorted;
}
export function exStats(runs:ExRun[],start='',end='',quest=''){
 const rows=runs.filter(r=>(!start||r.date>=start)&&(!end||r.date<=end)&&(!quest||r.quest===quest));
 const spawns=rows.filter(r=>r.spawned).length;
 return {runs:rows.length,spawns,rate:rows.length?spawns/rows.length:0};
}
export function exportCsv(rows:(string|number|boolean|null|undefined)[][]){return '\uFEFF'+rows.map(r=>r.map(x=>'"'+String(x??'').replace(/"/g,'""')+'"').join(',')).join('\r\n');}
export function downloadCsv(text:string,name:string){const blob=new Blob([text],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
export function normalizedBondHistory(b:Bond){return Array.isArray(b.history)?b.history:[];}
export function playWinRate(rows:PlayLog[]){return {total:rows.length,wins:rows.filter(r=>r.result==='勝利').length,rate:rows.length?rows.filter(r=>r.result==='勝利').length/rows.length:0};}
export function partyFromTeam(state:AppState,teamId:string):PartyMember[]{
 const team=state.teams.find(t=>t.id===teamId);if(!team)return [];
 return team.slots.flatMap(id=>{const owned=state.owned.find(o=>o.id===id);const character=state.catalog.find(c=>c.id===owned?.characterId);return owned&&character?[{owned,character}]:[];});
}
