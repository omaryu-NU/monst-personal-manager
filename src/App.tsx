import { useEffect, useMemo, useRef, useState, type ChangeEvent, type ReactNode } from 'react';
import { LayoutDashboard, BookOpen, Users, Shield, ListTodo, Calculator, BarChart3, Settings, Sparkles, Plus, Trash2, Download, Upload, Cloud, CloudOff, LogIn, LogOut, RefreshCw } from 'lucide-react';
import type { User } from 'firebase/auth';
import type { AppState, OwnedCharacter } from './types';
import { initialState, makeId } from './data';
import { downloadJson, loadLocal, loadRecovery, recoverySnapshot, saveLocal, validateState } from './persistence';
import { firebaseEnabled, listenAuth, login, logout } from './firebase';
import { SECTIONS, changedSections, fetchRemote, saveSections, watchRemote, ConflictError, type Versions, type Section } from './sync';
import CatalogBrowser from './CatalogBrowser';
import {loadPublicCatalog,overlayCatalog} from './technophere-feed';
import type {Character} from './types';
import OwnedManager from './OwnedManager';
import QuestManager from './QuestManager';
import {CombatCalculator,PlayRecords} from './PlayTools';
import AnalyticsDashboard from './AnalyticsDashboard';
import PwaStatus from './PwaStatus';
import BackupManager from './BackupManager';
import { addBackup } from './backup-v10';
import { auditState } from './integrity-v10';
import { normalizeOwned, updateFruitSlot, fruitProgress, appendHistory, bulkUpdate, fruitLabel, type BulkPatch } from './owned-v05';
import type { FruitSlot } from './types';
import { readCatalogPackage, mergeCatalog, type CatalogPreview } from './catalog-v04';
import { readPending, writePending, clearPending, keepSafetyBackup, listSafetyBackups, describeSyncError, readCheckpoint, saveCheckpoint } from './sync-safety';

type Page = 'home'|'catalog'|'owned'|'teams'|'extras'|'calculator'|'analytics'|'settings';
const menu: {id:Page;label:string;icon:typeof LayoutDashboard}[] = [
 {id:'home',label:'ダッシュボード',icon:LayoutDashboard},{id:'catalog',label:'キャラ図鑑',icon:BookOpen},
 {id:'owned',label:'所持キャラ',icon:Users},{id:'teams',label:'編成管理',icon:Shield},
 {id:'extras',label:'周回・ToDo・予定',icon:ListTodo},{id:'calculator',label:'計算ツール',icon:Calculator},
 {id:'analytics',label:'分析',icon:BarChart3},{id:'settings',label:'設定・同期',icon:Settings}
];
function Card({title,children,actions}:{title:string;children:ReactNode;actions?:ReactNode}) {return <section className="card"><div className="card-heading"><h2>{title}</h2>{actions}</div>{children}</section>}
function fileReader(event:ChangeEvent<HTMLInputElement>, handler:(data:unknown)=>void) {
 const file=event.target.files?.[0]; if (!file) return; event.target.value='';
 if (file.size>8_000_000) {alert('ファイルは8MB以下にしてください');return;}
 file.text().then(t=>handler(JSON.parse(t))).catch(e=>alert('JSON読み込み失敗: '+String(e)));
}
export default function App(){
 const [state,setState] = useState<AppState>(loadLocal);
 const [publicCatalog,setPublicCatalog] = useState<Character[]>([]);
 const [publicCatalogInfo,setPublicCatalogInfo] = useState('図鑑マスター確認中');
 useEffect(()=>{const ctl=new AbortController();loadPublicCatalog(ctl.signal).then(({rows,updatedAt})=>{setPublicCatalog(rows);setPublicCatalogInfo(rows.length?`外部図鑑 ${rows.length}件 / 更新 ${updatedAt??'不明'}`:'外部図鑑は未配信（ローカル図鑑を使用）');}).catch(e=>{if(!ctl.signal.aborted)setPublicCatalogInfo('外部図鑑の読込失敗：'+String(e))});return()=>ctl.abort()},[]);
 const [page,setPage] = useState<Page>('home');
 const [analyticsOwnedFilter,setAnalyticsOwnedFilter]=useState<{attribute?:string;characterIds?:string[]}|null>(null);
 const [analyticsRunFilter,setAnalyticsRunFilter]=useState<{quest?:string;start?:string;end?:string}|null>(null);
 const [catalogPreview,setCatalogPreview]=useState<CatalogPreview|null>(null);
 const [user,setUser]=useState<User|null>(null);
 const [cloudStatus,setCloudStatus]=useState('ローカルモード');
 const [cloudReady,setCloudReady]=useState(false);
 const latest=useRef(state);
 const baseline=useRef<AppState|null>(null);
 const versions=useRef<Versions|null>(null);
 const dirty=useRef<Set<Section>>(new Set());
 const syncBusy=useRef(false);
 const readyRef=useRef(false);
 const [pendingTick,setPendingTick]=useState(0);
 const [conflict,setConflict]=useState(false);
 const [remoteMode,setRemoteMode]=useState<'none'|'legacy'|'v2'|null>(null);
 const [lastError,setLastError]=useState('');
 const [retryCount,setRetryCount]=useState(0);
 const [online,setOnline]=useState(()=>navigator.onLine);
 const [saving,setSaving]=useState(false);
 const [mobileMore,setMobileMore]=useState(false);
 const [sidebarCompact,setSidebarCompact]=useState(false);
 const sessionId=useRef(0);
 
 useEffect(()=>{latest.current=state;saveLocal(state)},[state]);
 useEffect(()=>{
  const onOnline=()=>{setOnline(true);setRetryCount(v=>v+1);setPendingTick(v=>v+1);};
  const onOffline=()=>{setOnline(false);setCloudStatus('オフライン：変更は端末に保存されます');};
  window.addEventListener('online',onOnline);window.addEventListener('offline',onOffline);
  return()=>{window.removeEventListener('online',onOnline);window.removeEventListener('offline',onOffline);};
 },[]);
 useEffect(()=>listenAuth(u=>{
  sessionId.current+=1;
  setUser(u);setCloudReady(false);readyRef.current=false;
  baseline.current=null;versions.current=null;dirty.current.clear();setConflict(false);
  setRemoteMode(null);setLastError('');
  setCloudStatus(u?'クラウド接続中':'ローカルモード');
 }),[]);
 useEffect(()=>{
  if(!user || !online)return;
  const uid=user.uid;const epoch=sessionId.current;
  let alive=true;let unsubscribe=()=>{};let loading=false;
  const isCurrent=()=>alive && sessionId.current===epoch;
  const reload=async(first:boolean)=>{
   if(loading || syncBusy.current)return;
   loading=true;
   try{
    const remote=await fetchRemote(uid,latest.current);
    if(!isCurrent())return;
    if(first){
      // Preserve the exact previous local state before ever applying cloud data.
      keepSafetyBackup(latest.current,'before-cloud-initialization');
      recoverySnapshot(latest.current);
      const storedPending=readPending(uid);
      const hasPending=storedPending.length>0;
      const checkpoint=readCheckpoint(uid);
      const pendingKeys=new Set(storedPending);
      // In a fresh account the local data is deliberately not uploaded without consent.
      if(hasPending && remote.source!=='none'){
       const safeToResume=remote.source==='v2' && checkpoint &&
         storedPending.every(k=>checkpoint.versions[k]===remote.versions[k]);
       if(safeToResume){
        // Pending sections are kept locally; unrelated remote updates are incorporated.
        const merged={...remote.data};
        for(const key of storedPending)(merged as unknown as Record<string,unknown>)[key]=latest.current[key];
        const localMerged=validateState(merged);
        baseline.current=remote.data;versions.current=remote.versions;setRemoteMode('v2');
        latest.current=localMerged;setState(localMerged);
        dirty.current=new Set(pendingKeys);
        setCloudStatus('未同期のローカル編集を復旧しました。クラウド保存を再開します');
        setPendingTick(v=>v+1);
       }else{
        baseline.current=remote.data;versions.current=remote.versions;setRemoteMode(remote.source);
        dirty.current=new Set(pendingKeys);
        setConflict(true);setCloudStatus('競合の可能性：未同期の編集を保護しています');
       }
      } else {
       baseline.current=remote.data;versions.current=remote.versions;setRemoteMode(remote.source);
       if(remote.source!=='none'){
        const localBefore=latest.current;
        if(JSON.stringify(localBefore)!==JSON.stringify(remote.data))keepSafetyBackup(localBefore,'before-cloud-load');
        latest.current=remote.data;setState(remote.data);
       }
       if(!hasPending){dirty.current.clear();clearPending(uid);} else {dirty.current=new Set(pendingKeys);}
       setCloudStatus(remote.source==='none'?'クラウドは空です。ローカルデータの手動アップロードが可能です':remote.source==='legacy'?'旧形式クラウドを読み込みました。移行するにはアップロードしてください':'同期完了');
      }
      if(remote.source==='v2' && !hasPending)saveCheckpoint(uid,{versions:remote.versions,baseline:remote.data});
      readyRef.current=true;setCloudReady(true);setLastError('');
    }else{
      if(dirty.current.size){
       const changedRemotely=SECTIONS.some(k=>remote.versions[k] !== (versions.current?.[k]??0));
       if(changedRemotely){
        // Refuse unsafe overwrite: a conservative conflict is recoverable.
        setConflict(true);setCloudStatus('競合を検出：未同期の変更を保護しています');
       }
       return;
      }
      if(remote.source==='none')return;
      if(JSON.stringify(remote.data)!==JSON.stringify(latest.current)){
       keepSafetyBackup(latest.current,'before-remote-update');
       latest.current=remote.data;setState(remote.data);
      }
      baseline.current=remote.data;versions.current=remote.versions;setRemoteMode(remote.source);
      if(remote.source==='v2')saveCheckpoint(uid,{versions:remote.versions,baseline:remote.data});
      setCloudStatus('同期完了');setLastError('');
    }
   }catch(e){if(isCurrent()){
    const msg=describeSyncError(e);setLastError(msg);setCloudStatus('接続エラー：'+msg);
   }}finally{loading=false;}
  };
  void reload(true).then(()=>{if(isCurrent())unsubscribe=watchRemote(uid,()=>{
   if(readyRef.current)void reload(false);
  },e=>{if(isCurrent()){setLastError(describeSyncError(e));setCloudStatus('監視エラー：'+describeSyncError(e));}});});
  return()=>{alive=false;unsubscribe();};
 },[user,retryCount,online]);
 useEffect(()=>{
  if(!user||!cloudReady||remoteMode!=='v2'||!pendingTick||conflict||!online)return;
  const timer=setTimeout(async()=>{
    if(syncBusy.current||!versions.current||!baseline.current)return;
    const snapshot=latest.current;
    const diff=changedSections(baseline.current,snapshot);
    if(!diff.length){dirty.current.clear();clearPending(user.uid);setCloudStatus('同期完了');return;}
    syncBusy.current=true;setSaving(true);
    try {
      setCloudStatus('クラウドに保存中');
      const next=await saveSections(user.uid,snapshot,diff,versions.current);
      versions.current=next;baseline.current=snapshot;saveCheckpoint(user.uid,{versions:next,baseline:snapshot});
      for(const key of diff)if(JSON.stringify(latest.current[key])===JSON.stringify(snapshot[key]))dirty.current.delete(key);
      writePending(user.uid,[...dirty.current]);
      setCloudStatus(dirty.current.size?'追加変更の保存待ち':'同期完了');setLastError('');
      if(dirty.current.size)setPendingTick(x=>x+1);
    }catch(e){const msg=describeSyncError(e);setLastError(msg);setCloudStatus('同期失敗：'+msg);if(e instanceof ConflictError)setConflict(true);}
    finally{syncBusy.current=false;setSaving(false);}
  },700);
  return()=>clearTimeout(timer);
 },[pendingTick,user,cloudReady,remoteMode,conflict,online]);
 const edit=(fn:(v:AppState)=>AppState)=>{
   const before=latest.current;const after=fn(before);
   const changed=changedSections(before,after);
   if(!changed.length)return;
   keepSafetyBackup(before,'before-local-edit');
   recoverySnapshot(before);
   for(const key of changed)dirty.current.add(key);
   try{saveLocal(after)}catch(e){setLastError('端末への保存に失敗しました: '+String(e));setCloudStatus('端末保存エラー：変更を反映しませんでした');alert('端末の空き容量不足などで保存に失敗しました。JSONバックアップを取得してください。');return;}
   latest.current=after;setState(after);setPendingTick(v=>v+1);
   if(user)writePending(user.uid,[...dirty.current]);
   setCloudStatus(!user?'ローカル保存済み':!online?'オフライン：変更を端末内に保存':!cloudReady?'接続待ち（ローカル保存済み）':remoteMode==='v2'?'保存待ち':'ローカル保存済み（初回アップロードが必要）');
 };
 const uploadAll=async()=>{
   if(!user||!cloudReady||syncBusy.current||!online)return;
   const integrityErrors=auditState(latest.current).filter(x=>x.level==='error');
   if(integrityErrors.length){alert('参照整合性エラーがあるためクラウドへの強制上書きを停止しました。設定画面のデータ診断を確認してください。');return;}
   if(!confirm('現在のローカルデータでクラウドを上書きします。別端末で編集中でないことを確認してください。続行しますか？'))return;
   const snapshot=latest.current;
   try{
    syncBusy.current=true;setSaving(true);keepSafetyBackup(snapshot,'before-manual-upload');recoverySnapshot(snapshot);
    // Explicit forced overwrite only after user confirmation; never on ordinary autosave.
    const next=await saveSections(user.uid,snapshot,[...SECTIONS],versions.current ?? Object.fromEntries(SECTIONS.map(k=>[k,0])) as Versions,true);
    versions.current=next;baseline.current=snapshot;saveCheckpoint(user.uid,{versions:next,baseline:snapshot});dirty.current.clear();clearPending(user.uid);setRemoteMode('v2');setConflict(false);setLastError('');setCloudStatus('手動アップロード完了');
   }catch(e){const msg=describeSyncError(e);setLastError(msg);setCloudStatus('アップロード失敗：'+msg);}
   finally{syncBusy.current=false;setSaving(false);}
 };
 const resolveConflict=async()=>{
   if(!user||!confirm('クラウドの最新状態を読み込みます。未同期のローカル編集は復旧バックアップに残ります。続行しますか？'))return;
   keepSafetyBackup(latest.current,'before-conflict-resolution');recoverySnapshot(latest.current);
   try{const remote=await fetchRemote(user.uid,latest.current);if(remote.source==='none')throw Error('クラウドのデータがありません');latest.current=remote.data;setState(remote.data);baseline.current=remote.data;versions.current=remote.versions;if(remote.source==='v2')saveCheckpoint(user.uid,{versions:remote.versions,baseline:remote.data});dirty.current.clear();clearPending(user.uid);setConflict(false);setRemoteMode(remote.source);setCloudStatus('クラウドから読み込みました');setLastError('');}
   catch(e){setCloudStatus('再読み込み失敗：'+describeSyncError(e));}
 };
 const account=state.accounts.find(a=>a.id===state.activeAccountId)??state.accounts[0];
 const owned=state.owned.filter(x=>x.accountId===account.id); const teams=state.teams.filter(x=>x.accountId===account.id);
 const todos=state.todos.filter(x=>x.accountId===account.id); const runs=state.runs.filter(x=>x.accountId===account.id);
 const bonds=state.bonds.filter(x=>x.accountId===account.id); const events=state.events.filter(x=>x.accountId===account.id);
 const effectiveCatalog=useMemo(()=>overlayCatalog(state.catalog,publicCatalog),[state.catalog,publicCatalog]);
 const catalogMap=useMemo(()=>new Map(effectiveCatalog.map(c=>[c.id,c])),[effectiveCatalog]);

 const addOwned=(characterId:string)=>edit(s=>({...s,catalog:s.catalog.some(c=>c.id===characterId)?s.catalog:[...s.catalog,...effectiveCatalog.filter(c=>c.id===characterId)],owned:[...s.owned,{id:makeId(),characterId,accountId:account.id,luck:1,level:1,memo:'',fruits:[],completed:false,fruitSlots:[],fruitTargets:[],history:[],tags:[],favorite:false,trainingStatus:'未育成',plusValues:{hp:0,attack:0,speed:0}}]}));
 const updateOwned=(id:string,patch:Partial<OwnedCharacter>,action='個体情報更新')=>edit(s=>({...s,owned:s.owned.map(item=>{
  if(item.id!==id)return item;
  const original=normalizeOwned(item);
  const merged={...original,...patch};
  // Keep v0.4 string fields in sync with structured slot data for older clients.
  if(patch.fruitSlots)merged.fruits=patch.fruitSlots.map(fruitLabel).filter(Boolean);
  if(patch.fruitTargets)merged.targetFruits=patch.fruitTargets.map(fruitLabel).filter(Boolean);
  merged.completed=fruitProgress(merged).complete;
  return appendHistory(merged,action,'個体データを更新',makeId(),new Date().toISOString());
 })}));
 const updateFruit=(id:string,which:'fruitSlots'|'fruitTargets',index:number,slot:FruitSlot)=>edit(s=>({...s,owned:s.owned.map(item=>item.id!==id?item:appendHistory(updateFruitSlot(item,which,index,slot),which==='fruitSlots'?'実の変更':'厳選目標変更',`枠${index+1}`,makeId(),new Date().toISOString()))}));
 const duplicateOwned=(id:string)=>edit(s=>({...s,owned:[...s.owned,...s.owned.filter(item=>item.id===id).map(item=>({...normalizeOwned(item),id:makeId(),history:[],memo:item.memo+'（コピー）'}))]}));
 const updateOwnedBulk=(ids:string[],patch:BulkPatch)=>edit(s=>bulkUpdate(s,ids.filter(id=>s.owned.some(o=>o.id===id&&o.accountId===account.id)),patch,makeId,new Date().toISOString()));
 const removeOwned=(id:string)=>{if(!confirm('所持キャラを削除しますか？ 編成内の参照も解除します。'))return;edit(s=>({...s,owned:s.owned.filter(x=>x.id!==id),teams:s.teams.map(t=>({...t,slots:t.slots.map(slot=>slot===id?null:slot)}))}))};
 const onCatalog=(data:unknown)=>{try{
  const preview=readCatalogPackage(data,latest.current.catalog);
  setCatalogPreview(preview);
 }catch(e){alert('図鑑JSON検証エラー: '+String(e))}};
 const applyCatalog=()=>{
  if(!catalogPreview)return;
  const p=catalogPreview;
  const mergedPreview=mergeCatalog(latest.current.catalog,p.incoming);
  const catalogBytes=new TextEncoder().encode(JSON.stringify({value:mergedPreview,revision:1})).length;
  if(catalogBytes>800_000){alert(`取り込み後の図鑑データは約${Math.ceil(catalogBytes/1024)}KiBです。v0.3互換のFirestore同期では1セクション約800KiBを超えるため、同期データ保護のため反映を停止しました。分割保存に対応する次版で取り込んでください。`);return;}
  if(!confirm(`新規${p.added}件、更新${p.updated}件、変更なし${p.unchanged}件を反映しますか？既存のキャラ・所持・編成情報は削除しません。`))return;
  keepSafetyBackup(latest.current,'before-catalog-v04-import');
  edit(s=>({...s,catalog:mergeCatalog(s.catalog,p.incoming)}));
  setCatalogPreview(null);
 };
 const onBackup=(data:unknown)=>{try{const parsed=validateState(data);const errors=auditState(parsed).filter(x=>x.level==='error');if(errors.length)throw Error('重大な整合性エラー: '+errors.slice(0,3).map(x=>x.path).join(', '));if(confirm('旧形式の復元です。復元前プレビュー機能の利用を推奨します。現在のデータを退避して置き換えますか？')){addBackup(latest.current,'before-legacy-json-restore');keepSafetyBackup(latest.current,'before-json-restore');edit(()=>parsed);alert('復元しました。クラウドへの反映状況をご確認ください')}}catch(e){alert(String(e))}};
 const stats=[{label:'所持キャラ',value:owned.length,detail:'同キャラの複数所持を含む',icon:Users},{label:'厳選完了',value:owned.filter(o=>fruitProgress(o).complete).length,detail:'所持キャラの完了数',icon:Sparkles},{label:'保存編成',value:teams.length,detail:'4枠のパーティ',icon:Shield},{label:'EX周回',value:runs.length,detail:`EX出現 ${runs.filter(x=>x.spawned).length} 回`,icon:RefreshCw}];
 return <div className="layout">
  <aside className={`sidebar ${sidebarCompact?'v09-sidebar-compact':''}`}><div className="brand"><div className="brand-mark">M</div><div><strong>MONST PERSONAL</strong><small>MY GAME DASHBOARD</small></div></div>
   <button className="v09-sidebar-toggle" aria-label={sidebarCompact?'サイドバーを展開':'サイドバーを折りたたむ'} onClick={()=>setSidebarCompact(x=>!x)}>{sidebarCompact?'»':'«'}</button><div className="side-sub">WORKSPACE</div><nav>{menu.map(m=><button title={m.label} key={m.id} className={page===m.id?'active':''} onClick={()=>setPage(m.id)}><m.icon size={18}/>{m.label}</button>)}</nav>
   <div className="sidebar-bottom"><div className="online-dot"/>{user?'Google同期有効':'ローカル保存'}<small>{user?.email??'Firebase設定で同期できます'}</small></div>
  </aside>
  <main className="main"><PwaStatus safeToUpdate={online && !saving && !conflict && dirty.current.size===0 && (!user || (cloudReady && remoteMode==='v2' && readPending(user.uid).length===0))}/><div className="v09-connectivity" role="status" aria-live="polite"><span className={online?'v09-online':'v09-offline'}>{online?'オンライン':'オフライン'}</span><span>{saving?'クラウド保存中':conflict?'同期競合：手動解決が必要':user?cloudStatus:'端末内に保存'}</span><span>未同期セクション：{dirty.current.size}</span>{lastError&&<button className="secondary" onClick={()=>setPage('settings')}>エラー詳細</button>}</div><header className="topbar"><div><span className="eyebrow">PERSONAL MANAGER / {menu.find(m=>m.id===page)?.label}</span><h1>{menu.find(m=>m.id===page)?.label}</h1></div><div className="header-actions"><select aria-label="使用アカウント" value={account.id} onChange={e=>edit(s=>({...s,activeAccountId:e.target.value}))}>{state.accounts.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select><button className="icon-button" title="設定" onClick={()=>setPage('settings')}><Settings size={19}/></button></div></header>
  {page==='home'&&<div className="stack"><div className="welcome"><span>WELCOME BACK</span><h2>あなたのモンスト管理を、ひとつに。</h2><p>キャラの所持・厳選・編成・周回をスマートに整理。</p><button className="primary" onClick={()=>setPage('catalog')}><BookOpen size={17}/>図鑑を見る</button></div><div className="stats">{stats.map(x=><div className="stat" key={x.label}><div className="stat-label">{x.label}<x.icon size={18}/></div><b>{x.value.toLocaleString()}</b><small>{x.detail}</small></div>)}</div><div className="columns"><Card title="クイックアクセス"><div className="quick-grid">{menu.filter(m=>!['home','settings'].includes(m.id)).slice(0,6).map(m=><button key={m.id} onClick={()=>setPage(m.id)}><m.icon size={23}/>{m.label}</button>)}</div></Card><Card title="最近の状況"><div className="overview"><div>図鑑登録<span>{effectiveCatalog.length}件</span></div><div>育成ToDo（未完了）<span>{todos.filter(t=>!t.done).length}件</span></div><div>イベント予定<span>{events.length}件</span></div><div>絆メーター登録<span>{bonds.length}件</span></div></div></Card></div></div>}
  {page==='catalog'&&<><p className="hint" role="status">{publicCatalogInfo}（所持・編成は既存Firebaseのまま）</p><CatalogBrowser catalog={effectiveCatalog} owned={owned} addOwned={addOwned}/></>}
  {page==='owned'&&<OwnedManager analyticsFilter={analyticsOwnedFilter} owned={owned} catalogMap={catalogMap} onPatch={updateOwned} onFruit={updateFruit} onRemove={removeOwned} onBulk={updateOwnedBulk} onDuplicate={duplicateOwned} onOpenCatalog={()=>setPage('catalog')}/> }
  {page==='teams'&&<QuestManager state={state} edit={edit} accountId={account.id}/>}
  {page==='extras'&&<PlayRecords analyticsRunFilter={analyticsRunFilter} state={state} accountId={account.id} edit={edit}/>}
  {page==='calculator'&&<CombatCalculator state={state} accountId={account.id}/>}
  {page==='analytics'&&<AnalyticsDashboard state={state} activeAccountId={account.id} onShowOwned={filter=>{setAnalyticsOwnedFilter(filter);setPage('owned')}} onShowRuns={filter=>{setAnalyticsRunFilter(filter);setPage('extras')}}/>}
  {page==='settings'&&<div className="stack"><Card title="複数ゲームアカウント"><div className="account-list">{state.accounts.map(a=><div className="account-row" key={a.id}><b>{a.name}</b><div className="button-row"><button className="secondary" onClick={()=>{const name=prompt('新しい名前',a.name);if(name?.trim())edit(s=>({...s,accounts:s.accounts.map(x=>x.id===a.id?{...x,name:name.trim()}:x)}))}}>名前変更</button>{state.accounts.length>1&&<button className="danger-ghost" onClick={()=>{if(!confirm(`${a.name}を削除しますか？関連データも削除されます。`))return; edit(s=>({...s,accounts:s.accounts.filter(x=>x.id!==a.id),activeAccountId:s.activeAccountId===a.id?s.accounts.find(x=>x.id!==a.id)!.id:s.activeAccountId,owned:s.owned.filter(x=>x.accountId!==a.id),teams:s.teams.filter(x=>x.accountId!==a.id).map(t=>({...t,slots:t.slots.map(slot=>s.owned.some(o=>o.id===slot&&o.accountId===a.id)?null:slot)})),quests:s.quests.filter(q=>q.accountId!==a.id),todos:s.todos.filter(x=>x.accountId!==a.id),runs:s.runs.filter(x=>x.accountId!==a.id),bonds:s.bonds.filter(x=>x.accountId!==a.id),events:s.events.filter(x=>x.accountId!==a.id),playLogs:(s.playLogs??[]).filter(x=>x.accountId!==a.id)}))}}><Trash2 size={16}/></button>}</div></div>)}</div><button className="primary" onClick={()=>{const name=prompt('アカウント名');if(name?.trim()){const id=makeId();edit(s=>({...s,accounts:[...s.accounts,{id,name:name.trim()}],activeAccountId:id}))}}}><Plus size={16}/>アカウント追加</button></Card><div className="columns"><Card title="図鑑データの更新"><p className="hint">権利・利用条件を確認したJSONデータを読み込みます。登録済みの所持キャラはIDで照合します。</p><label className="file-upload"><Upload size={17}/>キャラJSONをインポート<input type="file" accept=".json,application/json" onChange={e=>fileReader(e,onCatalog)}/></label>{catalogPreview&&<div className="catalog-preview" role="status"><b>図鑑取り込みプレビュー</b><p>出典：{catalogPreview.source}</p><p>新規 {catalogPreview.added}件 / 更新 {catalogPreview.updated}件 / 変更なし {catalogPreview.unchanged}件</p>{catalogPreview.warnings.map(w=><p className="hint" key={w}>{w}</p>)}<div className="button-row"><button className="primary" onClick={applyCatalog}>差分更新を確定</button><button className="secondary" onClick={()=>setCatalogPreview(null)}>キャンセル</button></div></div>}<button className="secondary" onClick={()=>downloadJson(state.catalog,'character-catalog.json')}><Download size={17}/>現在の図鑑をエクスポート</button><p className="hint">差分更新は同じキャラIDを更新し、未収録IDは残します。出典と利用条件が明確なJSONのみ利用してください。第三者サイトの自動収集は行いません。</p></Card><Card title="バックアップ・復元"><p className="hint">JSONファイルは所持・編成・設定・図鑑をすべて含みます。</p><button className="secondary" onClick={()=>downloadJson(state,`monst-backup-${new Date().toISOString().slice(0,10)}.json`)}><Download size={17}/>JSONバックアップ</button><label className="file-upload"><Upload size={17}/>JSONバックアップから復元<input type="file" accept=".json,application/json" onChange={e=>fileReader(e,onBackup)}/></label><button className="danger-ghost" onClick={()=>{if(confirm('すべてのデータを初期化しますか？ クラウドにも反映される可能性があります。')){try{addBackup(latest.current,'before-reset')}catch(e){alert('バックアップの保存に失敗しました。JSONを書き出してから再試行してください: '+String(e));return;}if(confirm('確認：データを初期化します。続行しますか？'))edit(()=>initialState())}}}>全データを初期化</button></Card></div><BackupManager state={state} restore={candidate=>edit(()=>candidate)}/><Card title="Googleログイン・オンライン同期"><div className="sync-status">{user?<Cloud size={19}/>:<CloudOff size={19}/>} {cloudStatus}</div>{!firebaseEnabled&&<p className="hint">.envのFirebase情報を設定してから再起動するとGoogleログインを使用できます。</p>}{firebaseEnabled&&!user&&<button className="primary" onClick={()=>login().catch(e=>alert('ログイン失敗: '+e.message))}><LogIn size={17}/>Googleでログイン</button>}{user&&<div className="stack"><p>{user.email} でログイン中</p>{lastError&&<p role="alert" className="hint">詳細: {lastError}</p>}{!online&&<p role="status" className="hint">インターネット未接続：操作内容は端末に保存されます。</p>}{!cloudReady&&online&&<button className="secondary" onClick={()=>setRetryCount(v=>v+1)}>クラウド接続を再試行</button>}{conflict&&<p role="alert" className="hint">競合しています。JSONバックアップ後に「クラウド最新を読み込む」、または手動アップロードを選択してください。</p>}<p className="hint">初回ログインで既存クラウドデータがあればクラウド側を優先します。ローカルデータを保持したい場合、ログイン前にJSONバックアップしてください。</p><div className="button-row"><button className="secondary" disabled={!cloudReady||!online||saving} onClick={()=>void uploadAll()}><Upload size={16}/>現在データをクラウドへ上書き</button><button className="secondary" onClick={()=>logout().catch(e=>alert(e.message))}><LogOut size={16}/>ログアウト</button>{conflict&&<button className="secondary" onClick={()=>void resolveConflict()}>クラウド最新を読み込む</button>}{dirty.current.size>0&&!conflict&&remoteMode==='v2'&&<button className="secondary" onClick={()=>setPendingTick(x=>x+1)}>保存を再試行</button>}</div></div>}<p className="hint">v0.2: 機能別のFirestore文書とリビジョン確認を使用します。旧v1のクラウド文書は削除しません。競合時は自動上書きを止め、手動で解決してください。オフラインの編集は端末内に残りますが、復帰後は保存再試行が必要な場合があります。</p><button className="secondary" onClick={()=>downloadJson(listSafetyBackups(),`monst-safety-history-${new Date().toISOString().slice(0,10)}.json`)}><Download size={16}/>復旧バックアップ履歴を書き出す</button><button className="secondary" onClick={()=>{const backup=loadRecovery();if(!backup)return alert('復旧スナップショットなし');if(confirm('ローカルの復旧スナップショットを読み込みますか？'))edit(()=>backup)}}>直前のローカル復旧データを読み込む</button></Card></div>}
  <footer>MONST PERSONAL MANAGER v1.0 · 非公式個人用ツール / ゲーム運営会社とは無関係</footer>
  </main><nav className="bottom-nav" aria-label="スマホ用ナビゲーション">{menu.filter(m=>['home','catalog','owned','teams'].includes(m.id)).map(m=><button key={m.id} aria-current={page===m.id?'page':undefined} className={page===m.id?'active':''} onClick={()=>{setMobileMore(false);setPage(m.id)}}><m.icon size={20}/><span>{m.id==='home'?'ホーム':m.id==='catalog'?'検索':m.id==='owned'?'所持':'編成'}</span></button>)}<button className={mobileMore||['extras','calculator','analytics','settings'].includes(page)?'active':''} aria-expanded={mobileMore} aria-controls="v09-more-menu" onClick={()=>setMobileMore(x=>!x)}><Settings size={20}/><span>その他</span></button></nav>{mobileMore&&<div id="v09-more-menu" className="v09-more" role="menu" aria-label="その他の画面">{menu.filter(m=>['extras','calculator','analytics','settings'].includes(m.id)).map(m=><button role="menuitem" key={m.id} onClick={()=>{setPage(m.id);setMobileMore(false)}}><m.icon size={18}/>{m.label}</button>)}<button onClick={()=>setMobileMore(false)}>閉じる</button></div>}
 </div>
}
