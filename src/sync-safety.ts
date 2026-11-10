import type {AppState} from './types';
import type {Section, Versions} from './sync';
import {SECTIONS} from './sync';

const PENDING_PREFIX='monst-personal-v3-pending-';
const CHECKPOINT_PREFIX='monst-personal-v3-checkpoint-';
const BACKUPS_KEY='monst-personal-v3-safety-backups';
export type SafetyBackup={id:string;createdAt:string;reason:string;state:AppState};
export function readPending(uid:string):Section[]{
 try{const v=JSON.parse(localStorage.getItem(PENDING_PREFIX+uid)||'[]');return Array.isArray(v)?v.filter((x:unknown):x is Section=>typeof x==='string'&&SECTIONS.includes(x as Section)):[];}catch{return [];}
}
export function writePending(uid:string,sections:Section[]){localStorage.setItem(PENDING_PREFIX+uid,JSON.stringify([...new Set(sections)]));}
export function clearPending(uid:string){localStorage.removeItem(PENDING_PREFIX+uid);}
export function listSafetyBackups():SafetyBackup[]{
 try{const v=JSON.parse(localStorage.getItem(BACKUPS_KEY)||'[]');return Array.isArray(v)?v:[];}catch{return [];}
}
export function keepSafetyBackup(state:AppState,reason:string){
 // Snapshot errors must never interrupt ordinary edits; user still has JSON exports.
 try{
  const saved:SafetyBackup={id:crypto.randomUUID(),createdAt:new Date().toISOString(),reason,state:structuredClone(state)};
  const existing=listSafetyBackups();
  const next=[saved,...existing].slice(0,5);
  // Do not replace the previous valid backup if localStorage is full.
  localStorage.setItem(BACKUPS_KEY,JSON.stringify(next));
 }catch(e){console.warn('復旧バックアップを保存できませんでした。JSONエクスポートを推奨します。',e);}
}
export function describeSyncError(error:unknown):string{
 const e=error as {code?:string;message?:string};
 if(e?.code==='permission-denied')return 'Firestoreの権限がありません。ルールとGoogleアカウントを確認してください。';
 if(e?.code==='unavailable')return 'Firestoreに接続できません。通信状態を確認して再試行してください。';
 if(e?.code==='unauthenticated')return '認証の有効期限が切れました。再ログインしてください。';
 if(e?.code==='resource-exhausted')return '保存の上限に達しました。JSONバックアップを保存してください。';
 return typeof e?.message==='string'?e.message:String(error);
}

export type SyncCheckpoint={versions:Versions;baseline:AppState};
export function readCheckpoint(uid:string):SyncCheckpoint|null{
 try{const v=JSON.parse(localStorage.getItem(CHECKPOINT_PREFIX+uid)||'null');return v && typeof v==='object' && v.versions && v.baseline ? v as SyncCheckpoint:null;}catch{return null;}
}
export function saveCheckpoint(uid:string,checkpoint:SyncCheckpoint){
 try{localStorage.setItem(CHECKPOINT_PREFIX+uid,JSON.stringify(checkpoint));}catch(e){console.warn('同期チェックポイントの保存失敗',e);}
}
