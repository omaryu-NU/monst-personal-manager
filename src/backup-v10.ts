import type { AppState } from './types';
import {validateState} from './persistence';
import {auditState, summary, snapshotSize, type IntegrityIssue} from './integrity-v10';

export const HISTORY_KEY='monst-personal-v10-backup-history';
export type HistoryEntry={id:string;timestamp:string;reason:string;state:AppState};
export type BackupPreview={state:AppState;issues:IntegrityIssue[];counts:ReturnType<typeof summary>;size:number};
export function inspectBackup(value:unknown):BackupPreview{
 // Keep the original JSON intact until schema and references have been checked.
 const state=validateState(value);
 return {state,issues:auditState(state),counts:summary(state),size:snapshotSize(state)};
}
export function readBackupHistory(storage:Pick<Storage,'getItem'>=localStorage):HistoryEntry[]{
 try{
  const parsed:unknown=JSON.parse(storage.getItem(HISTORY_KEY)||'[]');
  if(!Array.isArray(parsed))return [];
  return parsed.flatMap(x=>{
   if(!x||typeof x!=='object')return [];
   const row=x as Partial<HistoryEntry>;
   if(typeof row.id!=='string'||typeof row.timestamp!=='string'||typeof row.reason!=='string')return [];
   try {return [{...row,state:validateState(row.state)} as HistoryEntry]} catch{return []}
  });
 }catch{return []}
}
export function addBackup(state:AppState,reason:string,storage:Pick<Storage,'getItem'|'setItem'>=localStorage):HistoryEntry[]{
 const item:HistoryEntry={id:crypto.randomUUID(),timestamp:new Date().toISOString(),reason,state:structuredClone(state)};
 const entries=[item,...readBackupHistory(storage)].slice(0,5);
 // Commit atomically at the single-key level; failure leaves old backups unchanged.
 storage.setItem(HISTORY_KEY,JSON.stringify(entries));
 return entries;
}
export function downloadBackupFile(state:AppState):string{
 return JSON.stringify({format:'monst-personal-v1',exportedAt:new Date().toISOString(),state},null,2);
}
export function parseBackupFile(raw:unknown):BackupPreview{
 if(raw && typeof raw==='object' && (raw as {format?:unknown}).format==='monst-personal-v1')return inspectBackup((raw as {state:unknown}).state);
 return inspectBackup(raw);
}
