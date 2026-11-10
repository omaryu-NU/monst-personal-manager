import { useEffect, useMemo, useState } from 'react';
import type { AppState, Quest, Team } from './types';
import { makeId } from './data';
import { downloadJson } from './persistence';
import { GIMMICKS, comparison, duplicateTeam, makeQuest, normalizeTeam, parseGimmicks, resolveSlot, restoreTeam, searchOwnedForQuest, teamSvg, updateTeamWithHistory } from './quest-v06';

type Props={state:AppState;edit:(fn:(s:AppState)=>AppState)=>void;accountId:string};
const today=()=>new Date().toISOString();
export default function QuestManager({state,edit,accountId}:Props){
 const [selectedQuest,setSelectedQuest]=useState('');
 const [query,setQuery]=useState('');
 const [allAccounts,setAllAccounts]=useState(false);
 const [compareIds,setCompareIds]=useState<string[]>([]);
 const [showHistory,setShowHistory]=useState('');
 useEffect(()=>{setSelectedQuest('');setCompareIds([]);setShowHistory('');},[accountId]);
 const quests=(state.quests??[]).filter(q=>q.accountId===accountId);
 const teams=state.teams.filter(t=>t.accountId===accountId);
 const byId=useMemo(()=>new Map(state.catalog.map(c=>[c.id,c])),[state.catalog]);
 const selected=quests.find(q=>q.id===selectedQuest);
 const visibleQuests=quests.filter(q=>(q.name+' '+q.difficulty+' '+q.gimmicks.join(' ')).toLowerCase().includes(query.toLowerCase()));
 const updateQuest=(id:string,patch:Partial<Quest>)=>edit(s=>({...s,quests:s.quests.map(q=>q.id===id?{...q,...patch,updatedAt:today()}:q)}));
 const addQuest=()=>{const name=prompt('クエスト名');if(!name?.trim())return;const q=makeQuest(accountId,makeId(),name.trim());edit(s=>({...s,quests:[...(s.quests??[]),q]}));setSelectedQuest(q.id)};
 const removeQuest=(id:string)=>{if(!confirm('クエストを削除しますか？関連編成は削除せず、以前のクエスト名を保持します。'))return;
  edit(s=>({...s,quests:s.quests.filter(q=>q.id!==id),teams:s.teams.map(t=>t.questId===id?{...t,questId:undefined}:t)}));setSelectedQuest('');};
 const addTeam=()=>{const quest=selected;edit(s=>({...s,teams:[...s.teams,{id:makeId(),accountId,name:'新しい編成',quest:quest?.name??'',gimmicks:quest?.gimmicks.join('、')??'',questId:quest?.id,slots:[null,null,null,null],favorite:false,history:[]}]}))};
 const changeTeam=(id:string,patch:Partial<Team>,action?:string)=>edit(s=>({...s,teams:s.teams.map(t=>t.id===id?updateTeamWithHistory(t,patch,makeId(),today(),action):t)}));
 const removeTeam=(id:string)=>{if(confirm('編成を削除しますか？削除前にJSONバックアップを推奨します。'))edit(s=>({...s,teams:s.teams.filter(t=>t.id!==id)}))};
 const exportImage=(t:Team)=>{const svg=teamSvg(t,state.quests??[],state.owned,state.catalog,state.accounts);const url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`team-${t.id}.svg`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
 const candidates=(q?:Quest)=>searchOwnedForQuest(state.owned,state.catalog,q?.gimmicks??[],accountId,allAccounts);
 const teamList=[...teams].sort((a,b)=>Number(!!b.favorite)-Number(!!a.favorite));
 const compare=compareIds.map(id=>teams.find(t=>t.id===id)).filter((t):t is Team=>!!t);
 return <div className="stack">
  <section className="card"><div className="card-heading"><h2>クエスト管理</h2><button className="primary" onClick={addQuest}>+ クエスト登録</button></div>
   <div className="quest-layout"><div><input aria-label="クエスト検索" value={query} onChange={e=>setQuery(e.target.value)} placeholder="クエスト名・ギミックで検索"/><div className="quest-list" style={{marginTop:12}}>
    <button className={'quest-choice '+(!selectedQuest?'selected':'')} onClick={()=>setSelectedQuest('')}>すべての編成<small>旧形式の編成もここに表示します</small></button>
    {visibleQuests.map(q=><button className={'quest-choice '+(selectedQuest===q.id?'selected':'')} key={q.id} onClick={()=>setSelectedQuest(q.id)}>{q.name}<small>{q.difficulty} / {q.gimmicks.join('、')||'ギミック未登録'}</small></button>)}
   </div></div><div>{selected?<div className="quest-form">
    <label>クエスト名<input value={selected.name} onChange={e=>updateQuest(selected.id,{name:e.target.value})}/></label>
    <label>難易度<input value={selected.difficulty} onChange={e=>updateQuest(selected.id,{difficulty:e.target.value})} placeholder="例：轟絶"/></label>
    <label>属性<select value={selected.attribute} onChange={e=>updateQuest(selected.id,{attribute:e.target.value as Quest['attribute']})}>{['その他','火','水','木','光','闇'].map(a=><option key={a}>{a}</option>)}</select></label>
    <div className="wide"><b>主要ギミック</b><div className="gimmick-chips">{GIMMICKS.map(g=><label key={g}><input type="checkbox" checked={selected.gimmicks.includes(g)} onChange={e=>updateQuest(selected.id,{gimmicks:e.target.checked?[...selected.gimmicks,g]:selected.gimmicks.filter(x=>x!==g)})}/>{g}</label>)}</div></div>
    <label className="wide">追加ギミック（カンマ区切り）<input value={selected.gimmicks.filter(g=>!GIMMICKS.includes(g as typeof GIMMICKS[number])).join('、')} onChange={e=>updateQuest(selected.id,{gimmicks:[...selected.gimmicks.filter(g=>GIMMICKS.includes(g as typeof GIMMICKS[number])),...parseGimmicks(e.target.value)]})}/></label>
    <label className="wide">攻略メモ<textarea rows={3} value={selected.memo} onChange={e=>updateQuest(selected.id,{memo:e.target.value})}/></label>
    <button className="danger-ghost" onClick={()=>removeQuest(selected.id)}>クエスト削除</button>
   </div>:<p className="hint">クエストを選択するとギミックや属性を編集できます。既存編成はそのまま残ります。</p>}</div></div>
  </section>
  <section className="card"><div className="card-heading"><h2>4枠編成・個体別管理</h2><button className="primary" onClick={addTeam}>+ 編成を作成</button></div>
   <div className="quest-toolbar"><label><input type="checkbox" checked={allAccounts} onChange={e=>setAllAccounts(e.target.checked)}/> サブアカウントの個体も表示</label><span className="small-muted">ギミックフィルタはアビリティ名称に基づく参考判定です。適正・コネクト発動条件などを保証しません。</span></div>
   {teamList.filter(t=>!selectedQuest||t.questId===selectedQuest).length===0&&<p className="empty">編成がありません。新しい編成を作成してください。</p>}
   {teamList.filter(t=>!selectedQuest||t.questId===selectedQuest).map(raw=>{const t=normalizeTeam(raw);const quest=(state.quests??[]).find(q=>q.id===t.questId);const choices=candidates(quest);return <div key={t.id} className="v06-panel">
    <div className="team-header-row"><h3>{t.favorite?'★ ':''}{t.name}</h3><div className="team-actions"><button className="secondary" onClick={()=>changeTeam(t.id,{favorite:!t.favorite},'お気に入り変更')}>{t.favorite?'★ 解除':'☆ お気に入り'}</button><label className="small-muted">比較 <input type="checkbox" checked={compareIds.includes(t.id)} onChange={e=>setCompareIds(a=>e.target.checked?[...a,t.id].slice(-4):a.filter(x=>x!==t.id))}/></label></div></div>
    <div className="quest-form" style={{marginTop:12}}>
     <label>編成名<input value={t.name} onChange={e=>changeTeam(t.id,{name:e.target.value})}/></label>
     <label>クエスト<select value={t.questId??''} onChange={e=>{const q=quests.find(q=>q.id===e.target.value);changeTeam(t.id,{questId:q?.id,quest:q?.name??t.quest,gimmicks:q?.gimmicks.join('、')??t.gimmicks},'クエスト変更')}}><option value="">旧形式・手動入力</option>{quests.map(q=><option value={q.id} key={q.id}>{q.name}</option>)}</select></label>
     {!quest&&<><label>クエスト名<input value={t.quest} onChange={e=>changeTeam(t.id,{quest:e.target.value})}/></label><label>ギミック<input value={t.gimmicks} onChange={e=>changeTeam(t.id,{gimmicks:e.target.value})}/></label></>}
     <label className="wide">編成メモ<input value={t.notes??''} onChange={e=>changeTeam(t.id,{notes:e.target.value})}/></label>
    </div>
    <div style={{margin:'10px 0'}}>{t.slots.map((slot,i)=>{const detail=resolveSlot(slot,state.owned,state.catalog,state.accounts);return <div className="team-slot-line" key={i}>
     <b>枠 {i+1}</b><select aria-label={`${t.name} ${i+1}枠`} value={slot??''} onChange={e=>changeTeam(t.id,{slots:t.slots.map((v,j)=>i===j?(e.target.value||null):v)},'個体変更')}><option value="">未設定</option>
     {slot&&!choices.some(o=>o.id===slot)&&detail.instance&&<option value={slot}>{detail.character?.name??'不明'}（選択中・条件外）</option>}
     {choices.map(o=><option key={o.id} value={o.id}>{byId.get(o.characterId)?.name??'不明'} / {state.accounts.find(a=>a.id===o.accountId)?.name} / #{o.id.slice(0,6)}</option>)}</select>
     <div className="v09-swap"><button className="secondary" aria-label={`枠${i+1}を前の枠と交換`} disabled={i===0} onClick={()=>{const slots=[...t.slots];[slots[i-1],slots[i]]=[slots[i],slots[i-1]];changeTeam(t.id,{slots},'枠の入れ替え')}}>↑</button><button className="secondary" aria-label={`枠${i+1}を次の枠と交換`} disabled={i===3} onClick={()=>{const slots=[...t.slots];[slots[i+1],slots[i]]=[slots[i],slots[i+1]];changeTeam(t.id,{slots},'枠の入れ替え')}}>↓</button></div>
     <small className="team-slot-description">{detail.instance?`個体 #${detail.instance.id.slice(0,8)} ・ ${detail.account?.name??'アカウント不明'} ・ 厳選 ${detail.fruit?.percent??0}% ・ ${detail.instance.trainingStatus??'未設定'}`:'キャラを選択してください'}{slot&&!detail.instance?'（参照先が見つかりません）':''}</small>
    </div>})}</div>
    <div className="team-actions"><button className="secondary" onClick={()=>edit(s=>({...s,teams:[...s.teams,duplicateTeam(t,makeId())]}))}>複製</button><button className="secondary" onClick={()=>downloadJson(t,`team-${t.id}.json`)}>JSON出力</button><button className="secondary" onClick={()=>exportImage(t)}>画像(SVG)出力</button><button className="secondary" onClick={()=>setShowHistory(showHistory===t.id?'':t.id)}>履歴 ({t.history?.length??0})</button><button className="danger-ghost" onClick={()=>removeTeam(t.id)}>削除</button></div>
    {showHistory===t.id&&<div className="team-history">{!t.history?.length&&<p className="hint">履歴はありません。</p>}{[...(t.history??[])].reverse().map(h=><div className="simple-row" key={h.id}><span className="small-muted">{new Date(h.at).toLocaleString('ja-JP')} ・ {h.action}</span><button className="secondary" onClick={()=>{if(confirm('この時点の編成に復元しますか？現在の編成は履歴に残ります。'))edit(s=>({...s,teams:s.teams.map(x=>x.id===t.id?restoreTeam(x,h.id,makeId(),today()):x)}))}}>復元</button></div>)}</div>}
   </div>})}
  </section>
  <section className="card"><div className="card-heading"><h2>ギミック対応検索</h2></div>
   <p className="hint">上でクエストを選択してください。全ギミックに対応する可能性のある所持個体を抽出します。</p>
   {selected&&<div><p>対象：{selected.name} / {selected.gimmicks.join('、')||'ギミック指定なし'}</p><p className="small-muted">候補 {candidates(selected).length}体</p><div className="quest-list">{candidates(selected).slice(0,100).map(o=><div className="simple-row" key={o.id}>{byId.get(o.characterId)?.name}　<small>{state.accounts.find(a=>a.id===o.accountId)?.name} / {o.id.slice(0,8)}</small></div>)}</div></div>}
  </section>
  {compare.length>0&&<section className="card"><div className="card-heading"><h2>編成比較（最大4編成）</h2></div><div style={{overflowX:'auto'}}><table className="team-compare-table"><thead><tr><th>比較項目</th>{compare.map(t=><th key={t.id}>{t.name}</th>)}</tr></thead><tbody>{[0,1,2,3].map(i=><tr key={i}><th>枠 {i+1}</th>{compare.map(t=>{const r=comparison(t,state.quests??[],state.owned,state.catalog)[i];return <td key={t.id}>{r.characterName}<br/>対応 {r.matched.length}/{r.total} ギミック<br/>厳選 {r.fruitPercent}%</td>})}</tr>)}</tbody></table></div></section>}
 </div>;
}
