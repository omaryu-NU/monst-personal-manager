import type { AppState, Character } from './types';
import { initialState } from './data';
import { normalizeOwned } from './owned-v05';
export const KEY = 'monst-personal-v1';
const SAFETY_KEY='monst-personal-v2-recovery';
export const recoverySnapshot = (value:AppState) => localStorage.setItem(SAFETY_KEY,JSON.stringify({savedAt:new Date().toISOString(),state:value}));
export const loadRecovery = ():AppState | null => {try{const raw=localStorage.getItem(SAFETY_KEY);return raw?validateState(JSON.parse(raw).state):null;}catch{return null;}};
export const saveLocal = (value: AppState) => localStorage.setItem(KEY, JSON.stringify(value));
export function loadLocal(): AppState {
  try { const raw = localStorage.getItem(KEY); if(!raw)return initialState(); const original=JSON.parse(raw); const migrated=validateState(original); if(JSON.stringify(original)!==JSON.stringify(migrated) && !localStorage.getItem('monst-personal-v04-migration-backup'))localStorage.setItem('monst-personal-v04-migration-backup',raw); return migrated; }
  catch (error) { console.error('既存データを読み込めません。元データは削除せず、初期画面で起動します。バックアップからの復元を検討してください。',error); return initialState(); }
}
export function validateState(x: unknown): AppState {
 if (!x || typeof x !== 'object') throw new Error('バックアップ形式が不正です');
 const v = x as Record<string,unknown>;
 if (v.schemaVersion !== 1 || !Array.isArray(v.accounts) || !Array.isArray(v.catalog) || !Array.isArray(v.owned) || !Array.isArray(v.teams) || !Array.isArray(v.todos) || !Array.isArray(v.runs) || !Array.isArray(v.bonds) || !Array.isArray(v.events) || typeof v.activeAccountId !== 'string') throw new Error('非対応のバックアップ形式です');
 if (!v.accounts.some(a => !!a && typeof a === 'object' && (a as {id?:string}).id === v.activeAccountId)) throw new Error('アカウント情報が不正です');
 for (const key of ['accounts','catalog','owned','teams','quests','todos','runs','bonds','events','playLogs'] as const) {
  if (Array.isArray(v[key]) && (v[key] as unknown[]).length > 50000) throw new Error('データ件数が多すぎます');
 }
 for (const section of ['accounts','catalog','owned','teams','todos','runs','bonds','events'] as const) {
  if ((v[section] as unknown[]).some(row=>!row||typeof row!=='object'||Array.isArray(row))) throw new Error(`${section}に不正な行があります`);
 }
 return {...v,quests:Array.isArray(v.quests)?v.quests:[],teams:(v.teams as AppState['teams']).map(t=>({...t,slots:Array.isArray(t.slots)?[...t.slots.slice(0,4),...Array(Math.max(0,4-t.slots.length)).fill(null)]:[null,null,null,null]})),owned:(v.owned as AppState['owned']).map(normalizeOwned),playLogs:Array.isArray(v.playLogs)?v.playLogs:[]} as AppState;
}
const attrs = new Set(['火','水','木','光','闇','その他']);
export function parseCatalog(data: unknown): Character[] {
 const rows: unknown = Array.isArray(data) ? data : (data && typeof data === 'object' ? (data as {characters?:unknown}).characters : undefined);
 if (!Array.isArray(rows) || rows.length === 0 || rows.length > 50000) throw new Error('キャラ配列（最大5万件）が必要です');
 const ids = new Set<string>();
 return rows.map((item,i) => {
  if (!item || typeof item !== 'object') throw new Error(`${i+1}件目のデータが不正です`);
  const c = item as Record<string,unknown>;
  if (typeof c.id !== 'string' || !c.id.trim() || typeof c.name !== 'string' || !c.name.trim() || typeof c.attribute !== 'string' || !attrs.has(c.attribute) || !Array.isArray(c.abilities) || !c.abilities.every(a => typeof a === 'string')) throw new Error(`${i+1}件目に必須情報が不足しています`);
  if (ids.has(c.id)) throw new Error(`重複ID: ${c.id}`); ids.add(c.id);
  return {id:c.id,name:c.name,attribute:c.attribute as Character['attribute'],abilities:c.abilities as string[],type:typeof c.type==='string'?c.type:undefined,style:typeof c.style==='string'?c.style:undefined,race:typeof c.race==='string'?c.race:undefined,evolution:typeof c.evolution==='string'?c.evolution:undefined,friendship:typeof c.friendship==='string'?c.friendship:undefined,ss:typeof c.ss==='string'?c.ss:undefined,source:typeof c.source==='string'?c.source:undefined,image: typeof c.image==='string' && /^https:\/\//.test(c.image)?c.image:undefined};
 });
}
export function downloadJson(data: unknown, filename: string) {
 const blob = new Blob([JSON.stringify(data,null,2)],{type:'application/json'}); const url = URL.createObjectURL(blob);
 const a = document.createElement('a'); a.href=url; a.download=filename; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}
