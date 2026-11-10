import type { AppState } from './types';

export type IntegrityIssue = { level:'error'|'warning'; path:string; message:string };
export type StateSummary = { accounts:number; catalog:number; owned:number; teams:number; quests:number; todos:number; runs:number; bonds:number; events:number; playLogs:number };
export const summary = (state:AppState):StateSummary=>({accounts:state.accounts.length,catalog:state.catalog.length,owned:state.owned.length,teams:state.teams.length,quests:state.quests.length,todos:state.todos.length,runs:state.runs.length,bonds:state.bonds.length,events:state.events.length,playLogs:state.playLogs?.length??0});
const issue=(level:IntegrityIssue['level'],path:string,message:string):IntegrityIssue=>({level,path,message});
export function auditState(s:AppState):IntegrityIssue[]{
 const out:IntegrityIssue[]=[];
 const sections=['accounts','catalog','owned','teams','quests','todos','runs','bonds','events','playLogs'] as const;
 for(const key of sections){
  const values=s[key]??[];
  const ids=new Set<string>();
  for(const [index,row] of values.entries()){
   const id=(row as {id?:unknown})?.id;
   if(typeof id!=='string'||!id.trim())out.push(issue('error',`${key}[${index}].id`,'IDがありません'));
   else if(ids.has(id))out.push(issue('error',`${key}[${index}].id`,'IDが重複しています'));
   else ids.add(id);
  }
 }
 const accounts=new Set(s.accounts.map(a=>a.id));
 const catalog=new Set(s.catalog.map(c=>c.id));
 const owned=new Map(s.owned.map(x=>[x.id,x]));
 const teams=new Map(s.teams.map(x=>[x.id,x]));
 const quests=new Map(s.quests.map(x=>[x.id,x]));
 if(!accounts.has(s.activeAccountId))out.push(issue('error','activeAccountId','有効なアカウントを参照していません'));
 for(const [i,o] of s.owned.entries()){
  if(!accounts.has(o.accountId))out.push(issue('error',`owned[${i}].accountId`,'アカウントがありません'));
  if(!catalog.has(o.characterId))out.push(issue('warning',`owned[${i}].characterId`,'図鑑にないキャラIDです（所持情報は保持します）'));
  if(!Number.isFinite(o.luck)||o.luck<0||o.luck>999)out.push(issue('error',`owned[${i}].luck`,'ラックが不正です'));
  if(!Number.isFinite(o.level)||o.level<0||o.level>999)out.push(issue('error',`owned[${i}].level`,'レベルが不正です'));
 }
 for(const [i,t] of s.teams.entries()){
  if(!accounts.has(t.accountId))out.push(issue('error',`teams[${i}].accountId`,'アカウントがありません'));
  if(!Array.isArray(t.slots)||t.slots.length!==4)out.push(issue('error',`teams[${i}].slots`,'編成は4枠である必要があります'));
  for(const [j,id] of (t.slots??[]).entries())if(id!=null&&!owned.has(id))out.push(issue('warning',`teams[${i}].slots[${j}]`,'参照先の所持個体がありません（編成は保持します）'));
  if(t.questId&&!quests.has(t.questId))out.push(issue('warning',`teams[${i}].questId`,'参照先クエストがありません'));
 }
 for(const [i,q] of s.quests.entries())if(!accounts.has(q.accountId))out.push(issue('error',`quests[${i}].accountId`,'アカウントがありません'));
 for(const [i,t] of s.todos.entries()){
  if(!accounts.has(t.accountId))out.push(issue('error',`todos[${i}].accountId`,'アカウントがありません'));
  if(t.ownedId&&!owned.has(t.ownedId))out.push(issue('warning',`todos[${i}].ownedId`,'対象の所持個体がありません'));
  if(t.questId&&!quests.has(t.questId))out.push(issue('warning',`todos[${i}].questId`,'対象クエストがありません'));
 }
 for(const key of ['runs','bonds','events','playLogs'] as const){for(const [i,v] of (s[key]??[]).entries())if(!accounts.has(v.accountId))out.push(issue('error',`${key}[${i}].accountId`,'アカウントがありません'))}
 for(const [i,p] of (s.playLogs??[]).entries()){
  if(p.questId&&!quests.has(p.questId))out.push(issue('warning',`playLogs[${i}].questId`,'参照先クエストがありません'));
  if(p.teamId&&!teams.has(p.teamId))out.push(issue('warning',`playLogs[${i}].teamId`,'参照先編成がありません'));
 }
 return out;
}
export function criticalIssues(s:AppState):IntegrityIssue[]{return auditState(s).filter(i=>i.level==='error')}
export const snapshotSize=(s:AppState):number=>new TextEncoder().encode(JSON.stringify(s)).byteLength;
