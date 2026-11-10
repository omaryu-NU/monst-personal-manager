import { collection, doc, getDocFromServer, getDocsFromServer, onSnapshot, runTransaction, serverTimestamp, type Unsubscribe } from 'firebase/firestore';
import { firestore } from './firebase';
import { validateState } from './persistence';
import type { AppState } from './types';

export const SECTIONS = ['catalog','accounts','activeAccountId','owned','teams','quests','todos','runs','bonds','events','playLogs'] as const;
export type Section = typeof SECTIONS[number];
export type Versions = Record<Section, number>;
const emptyVersions = (): Versions => Object.fromEntries(SECTIONS.map(k => [k,0])) as Versions;
export type Remote = { data: AppState; versions: Versions; source: 'v2'|'legacy'|'none' };
const basePath = (uid:string) => ['users',uid,'data'] as const;
const refSection = (uid:string,section:Section) => doc(firestore(),...basePath(uid),section);
const MAX_DOC_BYTES = 850_000;
const bytes = (v:unknown) => new TextEncoder().encode(JSON.stringify(v)).length;
export function changedSections(a:AppState,b:AppState): Section[] {return SECTIONS.filter(k => JSON.stringify(a[k])!==JSON.stringify(b[k]));}
export function mergeParts(base:AppState, updates:Partial<AppState>):AppState {return validateState({...base,...updates});}
export async function fetchRemote(uid:string, fallback:AppState):Promise<Remote>{
 const db=firestore();
 const query=await getDocsFromServer(collection(db,...basePath(uid)));
 if(!query.empty){
  const versions=emptyVersions(); const partial:Record<string,unknown>={};
  query.forEach(s=>{const key=s.id as Section; if(!SECTIONS.includes(key))return;const v=s.data();partial[key]=v.value;versions[key]=Number(v.revision)||0;});
  return {data:mergeParts(fallback,partial),versions,source:'v2'};
 }
 const old=await getDocFromServer(doc(db,'users',uid,'private','state'));
 if(old.exists())return {data:validateState(old.data().payload),versions:emptyVersions(),source:'legacy'};
 return {data:fallback,versions:emptyVersions(),source:'none'};
}
export class ConflictError extends Error {constructor(){super('別端末による変更を検出しました。現在の内容はローカルに保持しています。JSONバックアップ後、クラウドを再読み込みするか手動で上書きを選択してください。');this.name='ConflictError';}}
export async function saveSections(uid:string, local:AppState, changed:Section[], expected:Versions, overwrite=false):Promise<Versions>{
 if(!changed.length)return expected;
 const payloads=changed.map(key=>({key,value:local[key], ref:refSection(uid,key)}));
 for(const item of payloads){if(bytes({value:item.value,revision:1})>MAX_DOC_BYTES)throw Error(`${item.key} のデータが大きすぎます。現在の版ではこの項目をクラウド保存できません。JSONバックアップを作成してください。`);}
 return runTransaction(firestore(),async tx=>{
  const snaps=[];
  for(const item of payloads)snaps.push(await tx.get(item.ref));
  if(!overwrite && snaps.some((snap,i)=>(snap.exists()?Number(snap.data()?.revision)||0:0)!==expected[payloads[i].key]))throw new ConflictError();
  const next={...expected};
  for(let i=0;i<payloads.length;i++){
   const item=payloads[i];const rev=(snaps[i].exists()?Number(snaps[i].data()?.revision)||0:0)+1;
   tx.set(item.ref,{value:item.value,revision:rev,updatedAt:serverTimestamp()});next[item.key]=rev;
  }
  return next;
 });
}
export function watchRemote(uid:string,onChanged:()=>void,onError:(e:Error)=>void):Unsubscribe{
 return onSnapshot(collection(firestore(),...basePath(uid)),{includeMetadataChanges:false}, snap=>{if(!snap.metadata.hasPendingWrites && !snap.metadata.fromCache)onChanged();},onError);
}
