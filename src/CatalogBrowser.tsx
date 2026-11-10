import { useMemo, useState, useEffect } from 'react';
import type { Character, OwnedCharacter } from './types';
import { filterCatalog, type CatalogFilter } from './catalog-v04';
import VirtualList from './VirtualList';
import {addPreset,safeLoad,safeSave,type SearchPreset} from './search-v09';

type Props={catalog:Character[];owned:OwnedCharacter[];addOwned:(id:string)=>void};
const initial:CatalogFilter={term:'',attribute:'すべて',evolution:'すべて',type:'すべて',style:'すべて',race:'すべて',ability:'',ownedOnly:false};
function Options({label,values,value,onChange}:{label:string;values:string[];value:string;onChange:(s:string)=>void}){
 return <label className="catalog-field">{label}<select value={value} onChange={e=>onChange(e.target.value)}><option value="すべて">すべて</option>{values.map(v=><option key={v} value={v}>{v}</option>)}</select></label>;
}
const list=(catalog:Character[],key:'attribute'|'type'|'style'|'race'|'evolution')=>[...new Set(catalog.map(c=>c[key]).filter((x):x is string=>!!x))].sort((a,b)=>a.localeCompare(b,'ja'));
export default function CatalogBrowser({catalog,owned,addOwned}:Props){
 const [filter,setFilter]=useState<CatalogFilter>(()=>safeLoad('monst-v09-catalog-filter',initial));
 const [presets,setPresets]=useState<SearchPreset<CatalogFilter>[]>(()=>safeLoad('monst-v09-catalog-presets',[]));
 const [presetName,setPresetName]=useState('');
 const [history,setHistory]=useState<CatalogFilter[]>(()=>safeLoad('monst-v09-catalog-history',[]));
 useEffect(()=>{const t=window.setTimeout(()=>setHistory(previous=>{const existing=previous.filter(p=>JSON.stringify(p)!==JSON.stringify(filter));const next=[filter,...existing].slice(0,8);safeSave('monst-v09-catalog-history',next);return next}),900);return()=>window.clearTimeout(t)},[filter]);
 useEffect(()=>safeSave('monst-v09-catalog-filter',filter),[filter]);
 useEffect(()=>safeSave('monst-v09-catalog-presets',presets),[presets]);
 const [selectedId,setSelectedId]=useState<string|null>(null);

 const ownedIds=useMemo(()=>new Set(owned.map(o=>o.characterId)),[owned]);
 const found=useMemo(()=>filterCatalog(catalog,filter,ownedIds),[catalog,filter,ownedIds]);
 const selected=catalog.find(c=>c.id===selectedId);
 useEffect(()=>{if(!selectedId)return;const onKey=(e:KeyboardEvent)=>{if(e.key==='Escape')setSelectedId(null)};window.addEventListener('keydown',onKey);return()=>window.removeEventListener('keydown',onKey)},[selectedId]);
 const update=(key:keyof CatalogFilter,value:string|boolean)=>{setFilter(prev=>({...prev,[key]:value}));};
 return <div className="stack">
  <section className="card"><div className="card-heading"><h2>キャラクター図鑑</h2><span className="pill">{found.length} / {catalog.length}件</span></div>
   <div className="catalog-filters">
    <label className="catalog-field catalog-wide">名前・ID・性能のAND検索<input aria-label="名前と性能の検索" value={filter.term} onChange={e=>update('term',e.target.value)} placeholder="スペース区切りでAND検索"/></label>
    <label className="catalog-field catalog-wide">アビリティAND検索<input aria-label="アビリティ検索" value={filter.ability} onChange={e=>update('ability',e.target.value)} placeholder="例：アンチワープ マインスイーパー"/></label>
    <Options label="属性" values={list(catalog,'attribute')} value={filter.attribute} onChange={v=>update('attribute',v)}/>
    <Options label="進化形態" values={list(catalog,'evolution')} value={filter.evolution} onChange={v=>update('evolution',v)}/>
    <Options label="撃種" values={list(catalog,'type')} value={filter.type} onChange={v=>update('type',v)}/>
    <Options label="戦型" values={list(catalog,'style')} value={filter.style} onChange={v=>update('style',v)}/>
    <Options label="種族" values={list(catalog,'race')} value={filter.race} onChange={v=>update('race',v)}/>
   </div><div className="button-row"><label className="check-label"><input type="checkbox" checked={filter.ownedOnly} onChange={e=>update('ownedOnly',e.target.checked)}/>所持済みのみ</label><button className="secondary" onClick={()=>{setFilter(initial)}}>検索条件をリセット</button></div>
   <div className="v09-presets"><input aria-label="プリセット名" placeholder="検索条件の名前" value={presetName} onChange={e=>setPresetName(e.target.value)} /><button className="secondary" onClick={()=>{setPresets(p=>addPreset(p,presetName,filter));setPresetName('')}} disabled={!presetName.trim()}>検索条件を保存</button><select aria-label="検索プリセット" defaultValue="" onChange={e=>{const p=presets.find(x=>x.id===e.target.value);if(p)setFilter(p.filter);e.target.value=''}}><option value="">保存済み検索を選択</option>{presets.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select><select aria-label="検索履歴" defaultValue="" onChange={e=>{const i=Number(e.target.value);if(e.target.value&&history[i])setFilter(history[i]);e.target.value=''}}><option value="">検索履歴を選択</option>{history.map((h,i)=><option value={i} key={i}>{h.term||h.ability||h.attribute||'条件'} / {h.ownedOnly?'所持のみ':'全件'}</option>)}</select><button className="secondary" onClick={()=>{setHistory([]);safeSave('monst-v09-catalog-history',[])}}>履歴を削除</button><button className="secondary" onClick={()=>{const name=prompt('削除するプリセット名');if(name)setPresets(p=>p.filter(x=>x.name!==name))}}>プリセット削除</button></div>
   <p className="hint">実キャラのデータは利用条件を確認したJSONから取り込んでください。図鑑の更新は所持・編成情報を削除しません。</p>
  </section>
  {found.length>0&&<VirtualList items={found} keyFor={c=>c.id} ariaLabel="キャラクター図鑑の検索結果" estimateHeight={238} minWidth={280} renderItem={c=><article className="character-card" >
    <div className="char-main"><span className="char-icon">{c.image?<img alt="" loading="lazy" referrerPolicy="no-referrer" src={c.image} decoding="async"/>:c.name.slice(0,1)}</span><div><b>{c.name}</b><small>{c.attribute} / {c.evolution??'進化未設定'} / {c.type??'撃種未設定'}</small></div></div>
    <p>{[...c.abilities,...(c.gaugeAbilities??[]),...(c.connectAbilities??[])].join('・')||'アビリティ未登録'}</p>
    <div className="button-row"><button className="secondary" onClick={()=>setSelectedId(c.id)}>詳細</button><button onClick={()=>addOwned(c.id)}>所持に追加 ({owned.filter(o=>o.characterId===c.id).length})</button></div>
  </article>}/>}
  {found.length===0&&<p className="empty">条件に一致するキャラがありません</p>}
  {selected&&<div className="catalog-overlay" role="presentation" onClick={()=>setSelectedId(null)}><section role="dialog" aria-modal="true" tabIndex={-1} aria-label={`${selected.name}の詳細`} className="catalog-dialog" onClick={e=>e.stopPropagation()}><div className="card-heading"><h2>{selected.name}</h2><button className="secondary" onClick={()=>setSelectedId(null)}>閉じる</button></div>
   {selected.illustration&&<img className="catalog-illustration" alt={`${selected.name}のイラスト`} src={selected.illustration} referrerPolicy="no-referrer"/>}
   <dl className="catalog-details">{([['ID',selected.id],['属性',selected.attribute],['レアリティ',selected.rarity],['進化形態',selected.evolution],['種族',selected.race],['撃種',selected.type],['戦型',selected.style],['HP',selected.hp],['攻撃力',selected.attack],['スピード',selected.speed],['アビリティ',selected.abilities.join('・')],['ゲージ',selected.gaugeAbilities?.join('・')],['コネクト',selected.connectAbilities?.join('・')],['友情コンボ',selected.friendship],['副友情',selected.friendshipSub],['SS',selected.ss],['SSターン数',selected.strikeShotTurns],['出典',selected.source],['更新日',selected.updatedAt]] as [string,string|number|undefined][]).map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value??'未登録'}</dd></div>)}</dl>
   <button className="primary" onClick={()=>{addOwned(selected.id);setSelectedId(null)}}>所持キャラに追加</button></section></div>}
 </div>;
}
