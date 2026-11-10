import {useState,type ChangeEvent} from 'react';
import type {AppState} from './types';
import {auditState,summary} from './integrity-v10';
import {addBackup,readBackupHistory,parseBackupFile,type BackupPreview} from './backup-v10';
import {downloadJson} from './persistence';

export default function BackupManager({state,restore}:{state:AppState;restore:(s:AppState)=>void}){
 const [preview,setPreview]=useState<BackupPreview|null>(null);
 const [history,setHistory]=useState(()=>readBackupHistory());
 const [message,setMessage]=useState('');
 const issues=auditState(state);
 const counts=summary(state);
 const archive=(reason:string)=>{
  try{setHistory(addBackup(state,reason));setMessage('端末内の復元履歴に保存しました');return true}
  catch(e){setMessage('バックアップ保存に失敗しました。空き容量を確認しJSONを書き出してください。'+String(e));return false}
 };
 const onFile=async(e:ChangeEvent<HTMLInputElement>)=>{
  const file=e.target.files?.[0];e.target.value='';if(!file)return;
  if(file.size>15_000_000){setMessage('15MB以下のJSONファイルを選んでください');return}
  try{setPreview(parseBackupFile(JSON.parse(await file.text())));setMessage('内容を確認してから復元してください')}
  catch(err){setPreview(null);setMessage('読み込みに失敗しました: '+String(err))}
 };
 const restorePreview=(candidate:BackupPreview)=>{
  if(candidate.issues.some(x=>x.level==='error')){setMessage('重大な整合性エラーがあるため復元できません');return}
  if(!archive('before-manual-restore'))return;
  if(!confirm('復元すると現在の端末データが置き換わり、Firebaseにも同期される可能性があります。復旧履歴を保存しました。続行しますか？'))return;
  restore(candidate.state);setPreview(null);setMessage('復元を反映しました。同期状態を確認してください');
 };
 return <section className="card v10-backup" aria-labelledby="v10-backup-title">
  <div className="card-heading"><h2 id="v10-backup-title">v1.0 データ診断・安全なバックアップ</h2></div>
  <p className="hint">保存先・データ形式は従来のままです。復元前に件数と参照を検査します。端末内履歴はブラウザのデータ消去では失われるため、JSONも保存してください。</p>
  <p>アカウント {counts.accounts} / 図鑑 {counts.catalog} / 所持個体 {counts.owned} / 編成 {counts.teams} / プレイ履歴 {counts.playLogs}</p>
  <p role="status">整合性：重大 {issues.filter(x=>x.level==='error').length}件 / 要確認 {issues.filter(x=>x.level==='warning').length}件</p>
  {issues.slice(0,12).map((x,i)=><p className="hint" key={i}>{x.level==='error'?'要修正':'参照確認'}: {x.path} — {x.message}</p>)}
  <div className="button-row"><button className="secondary" onClick={()=>archive('manual-snapshot')}>端末内に復旧履歴を保存</button><button className="secondary" onClick={()=>downloadJson(state,'monst-personal-v10-backup.json')}>JSONをダウンロード</button><label className="file-upload">バックアップを検査して取り込む<input type="file" accept=".json,application/json" onChange={e=>void onFile(e)}/></label></div>
  {!!preview&&<div className="v10-preview" role="region" aria-label="復元前プレビュー"><h3>復元プレビュー</h3><p>図鑑 {preview.counts.catalog} / 所持 {preview.counts.owned} / 編成 {preview.counts.teams} / データ容量 {(preview.size/1024).toFixed(1)}KiB</p><p>重大な問題 {preview.issues.filter(x=>x.level==='error').length}件、要確認 {preview.issues.filter(x=>x.level==='warning').length}件</p>{preview.issues.slice(0,12).map((x,i)=><p className="hint" key={i}>{x.path}: {x.message}</p>)}<div className="button-row"><button className="primary" disabled={preview.issues.some(x=>x.level==='error')} onClick={()=>restorePreview(preview)}>確認して復元</button><button className="secondary" onClick={()=>setPreview(null)}>キャンセル</button></div></div>}
  <h3>復旧履歴（端末内・最大5件）</h3>{history.length===0&&<p className="hint">履歴はありません</p>}
  {history.map(item=><div className="v10-history-row" key={item.id}><span>{item.timestamp} — {item.reason}</span><button className="secondary" onClick={()=>{try{setPreview(parseBackupFile(item.state))}catch(err){setMessage(String(err))}}}>内容を確認</button></div>)}
  {message&&<p role="status">{message}</p>}
 </section>
}
