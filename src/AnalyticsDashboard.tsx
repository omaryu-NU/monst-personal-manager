import { useMemo, useState, type ReactNode } from 'react';
import { Download } from 'lucide-react';
import type { AppState } from './types';
import { accountComparison, analyticsCsv, analyticsData, type Breakdown, type Daily, type Period } from './analytics-v08';
import { downloadJson } from './persistence';
import { downloadCsv } from './play-v07';

type Props={state:AppState;activeAccountId:string;onShowOwned:(filter:{attribute?:string;characterIds?:string[]})=>void;onShowRuns:(filter:{quest?:string;start?:string;end?:string})=>void};
const pct=(value:number|null)=>value===null?'データなし':(value*100).toFixed(1)+'%';
const count=(n:number)=>n.toLocaleString('ja-JP');
const colors=['#7c94ff','#48bd9e','#f4b85b','#db7ea3','#a38df1','#7daabf','#6d92b9'];
function BarView({rows,onPick}:{rows:Breakdown;onPick?:(label:string)=>void}){
 const max=Math.max(1,...rows.map(x=>x.count));
 if(!rows.length)return <p className="hint">対象データがありません。</p>;
 return <div className="analytics-bars">{rows.map((r,i)=><div className="analytics-bar-row" key={r.label}>
 <button type="button" className="analytics-bar-label" disabled={!onPick} onClick={()=>onPick?.(r.label)} title={onPick?`${r.label}の所持キャラを表示`:r.label}>{r.label}</button>
 <div className="analytics-bar-rail"><div style={{width:`${r.count/max*100}%`,background:colors[i%colors.length]}}/></div><b>{count(r.count)}</b></div>)}</div>;
}
function PieView({rows}:{rows:Breakdown}){
 const sum=rows.reduce((n,r)=>n+r.count,0);let position=0;
 const gradient=rows.filter(r=>r.count).map((r,i)=>{const start=position;position+=r.count/sum*100;return `${colors[i%colors.length]} ${start}% ${position}%`;}).join(', ');
 return <div className="analytics-pie-layout"><div role="img" aria-label={rows.map(x=>`${x.label}${x.count}件`).join('、')} className="analytics-pie" style={{background:sum?`conic-gradient(${gradient})`:'#263550'}}><div><strong>{sum}</strong><small>合計</small></div></div><div className="analytics-legend">{rows.map((r,i)=><div key={r.label}><span style={{background:colors[i%colors.length]}}/>{r.label}<b>{count(r.count)}</b></div>)}</div></div>;
}
function LineView({rows,field}:{rows:Daily[];field:'runs'|'spawns'|'games'|'wins'}){
 if(rows.length===0)return <p className="hint">この期間の記録はありません。記録がない期間を0件として補完していません。</p>;
 const width=650,height=185,pad=27;
 const max=Math.max(1,...rows.map(r=>r[field]));
 const points=rows.map((r,i)=>({x:pad+(rows.length===1?0.5:i/(rows.length-1))*(width-2*pad),y:height-pad-r[field]/max*(height-2*pad),...r}));
 return <div className="analytics-chart-scroll"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${rows.length}記録日、最大${max}件の推移`} className="analytics-line">
 {[0,.25,.5,.75,1].map(t=><line key={t} x1={pad} x2={width-pad} y1={height-pad-t*(height-2*pad)} y2={height-pad-t*(height-2*pad)} stroke="#34435f" strokeWidth="1"/>)}
 <polyline points={points.map(p=>`${p.x},${p.y}`).join(' ')} fill="none" stroke="#8ea6ff" strokeWidth="3" strokeLinejoin="round"/>
 {points.map(p=><circle key={p.date} cx={p.x} cy={p.y} r="3.7" fill="#a3baff"><title>{`${p.date}: ${p[field]}件`}</title></circle>)}
 <text x={pad} y={height-5} fill="#a6b8d7" fontSize="11">{rows[0].date}</text><text x={width-pad} y={height-5} textAnchor="end" fill="#a6b8d7" fontSize="11">{rows[rows.length-1].date}</text>
 </svg></div>;
}
function Panel({title,children}:{title:string;children:ReactNode}){return <section className="card"><div className="card-heading"><h2>{title}</h2></div>{children}</section>}
export default function AnalyticsDashboard({state,activeAccountId,onShowOwned,onShowRuns}:Props){
 const [scope,setScope]=useState('active');
 const [start,setStart]=useState('');const [end,setEnd]=useState('');
 const [compareTo,setCompareTo]=useState('');
 const [dimension,setDimension]=useState<'attributes'|'types'|'styles'|'rarities'>('attributes');
 const [trend,setTrend]=useState<'runs'|'spawns'|'games'|'wins'>('runs');
 const accountIds=useMemo(()=>scope==='all'?state.accounts.map(a=>a.id):[scope==='active'?activeAccountId:scope],[scope,activeAccountId,state.accounts]);
 const period:Period={start,end};
 const d=useMemo(()=>analyticsData(state,accountIds,period),[state,accountIds,start,end]);
 const second=compareTo&&compareTo!==activeAccountId?compareTo:state.accounts.find(a=>a.id!==activeAccountId)?.id;
 const compare=second?accountComparison(state,activeAccountId,second):null;
 const dataJson={generatedAt:new Date().toISOString(),accountIds,period,summary:{...d,owned:undefined}};
 const selectOwned=(attribute?:string,characterIds?:string[])=>onShowOwned({attribute,characterIds});
 return <div className="stack analytics-v08">
  <div className="card"><div className="card-heading"><h2>分析条件</h2><span className="pill">v0.8</span></div>
  <div className="analytics-controls"><label>対象アカウント<select value={scope} onChange={e=>setScope(e.target.value)}><option value="active">現在のアカウント</option><option value="all">全アカウント</option>{state.accounts.map(a=><option value={a.id} key={a.id}>{a.name}</option>)}</select></label>
  <label>開始日<input type="date" value={start} onChange={e=>setStart(e.target.value)} max={end||undefined}/></label>
  <label>終了日<input type="date" value={end} onChange={e=>setEnd(e.target.value)} min={start||undefined}/></label>
  <button className="secondary" onClick={()=>{setStart('');setEnd('')}}>期間を解除</button>
  </div><p className="hint">期間指定はEX周回・プレイ履歴の記録日時に適用。所持・厳選は現在の状態であり、過去時点の推移を意味しません。</p>
  <div className="button-row"><button className="secondary" onClick={()=>downloadCsv(analyticsCsv(state,accountIds,period),'monst-analytics-v08.csv')}><Download size={15}/> CSVエクスポート</button><button className="secondary" onClick={()=>downloadJson(dataJson,'monst-analytics-v08.json')}><Download size={15}/> JSONエクスポート</button></div></div>
  <div className="stats analytics-cards">
   {[['所持個体',count(d.ownership.individuals),'重複所持を含む'],['所持種類',count(d.ownership.varieties),'図鑑外ID '+d.ownership.unknownVarieties+'種'],['図鑑所持率',pct(d.ownership.coverage.rate),'分母 '+d.ownership.catalogSize+'種類'],['厳選完了率',pct(d.fruit.rate.rate),'目標設定済み '+d.fruit.goalSet+'体'],['EX出現率（観測値）',pct(d.ex.rate.rate),d.ex.runs+'周 / '+d.ex.spawns+'回'],['プレイ勝率（記録値）',pct(d.play.rate.rate),d.play.games+'戦 / '+d.play.wins+'勝']].map(([label,value,detail])=><div className="stat" key={label}><span className="stat-label">{label}</span><b>{value}</b><small>{detail}</small></div>)}
  </div>
  <div className="columns"><Panel title="所持キャラ構成"><label>集計軸<select value={dimension} onChange={e=>setDimension(e.target.value as typeof dimension)}><option value="attributes">属性</option><option value="types">撃種</option><option value="styles">戦型</option><option value="rarities">レアリティ</option></select></label><BarView rows={d[dimension]} onPick={dimension==='attributes'?(label)=>selectOwned(label):undefined}/><p className="hint">属性名を選ぶと所持キャラ一覧へ移動します。不明項目は「未登録」に分類します。</p></Panel>
  <Panel title="わくわく厳選状況"><PieView rows={[{label:'完了',count:d.fruit.complete},{label:'未完了',count:d.fruit.incomplete},{label:'目標未設定',count:d.fruit.unset}]}/><p className="hint">完了率の分母は目標設定済み個体のみ。目標がない個体は未完了と区別しています。</p><button className="secondary" onClick={()=>selectOwned()}>所持キャラを確認</button></Panel></div>
  <div className="columns"><Panel title="育成とToDo"><div className="overview"><div>平均ラック（記録値）<span>{d.training.avgLuck?.toFixed(1)??'データなし'}</span></div><div>平均レベル（記録値）<span>{d.training.avgLevel?.toFixed(1)??'データなし'}</span></div><div>ToDo進捗<span>{d.training.todoDone}/{d.training.todoTotal}（{pct(d.training.todoRate.rate)}）</span></div></div><BarView rows={d.training.statuses}/></Panel>
  <Panel title="絆と編成利用"><div className="overview"><div>登録フレンド<span>{d.bonds.friends}人</span></div><div>絆の履歴件数<span>{d.bonds.historyEntries}件</span></div><div>平均絆進捗<span>{d.bonds.averageProgress?.toFixed(1)??'データなし'}</span></div></div><h3 className="analytics-subtitle">使用編成 TOP 5</h3>{d.play.byTeam.length?d.play.byTeam.slice(0,5).map(r=><div key={r.teamId} className="simple-row"><span>{state.teams.find(t=>t.id===r.teamId)?.name??'削除済みの編成'}</span><b>{r.count}回</b></div>):<p className="hint">編成IDが付いたプレイ履歴がありません。</p>}</Panel></div>
  <Panel title="EX周回・プレイの推移"><div className="analytics-controls"><label>グラフ<select value={trend} onChange={e=>setTrend(e.target.value as typeof trend)}><option value="runs">EX周回数</option><option value="spawns">EX出現回数</option><option value="games">プレイ件数</option><option value="wins">勝利数</option></select></label></div><LineView rows={d.daily} field={trend}/><p className="hint">記録が存在する日だけを接続しています。未記録の日はゼロ件とは限らないため補完しません。</p></Panel>
  <div className="columns"><Panel title="クエスト別 EX周回"><div className="overview"><div>記録周回数<span>{d.ex.runs}</span></div><div>EX出現数<span>{d.ex.spawns}</span></div><div>観測EX出現率<span>{pct(d.ex.rate.rate)}</span></div></div>{d.ex.byQuest.length?d.ex.byQuest.map(q=><button className="analytics-link-row" key={q.quest} onClick={()=>onShowRuns({quest:q.quest,start,end})}><span>{q.quest}</span><b>{q.denominator}周・{pct(q.rate)}</b></button>):<p className="hint">対象期間のEX記録がありません。</p>}<p className="hint">ゲーム内部の真の出現確率ではなく、入力された記録の割合です。</p></Panel>
  <Panel title="クエスト別プレイ成績">{d.play.byQuest.length?d.play.byQuest.map(q=><div className="simple-row" key={q.quest}><span>{q.quest}</span><b>{q.numerator}/{q.denominator}勝（{pct(q.rate)}）</b></div>):<p className="hint">対象期間のプレイ記録がありません。</p>}</Panel></div>
  <Panel title="アカウント比較"><div className="analytics-controls"><label>比較先<select value={second??''} disabled={!second} onChange={e=>setCompareTo(e.target.value)}>{state.accounts.filter(a=>a.id!==activeAccountId).map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select></label></div>{compare&&second?<><div className="analytics-compare"><div><b>{state.accounts.find(a=>a.id===activeAccountId)?.name}</b><p>所持 {compare.first.individuals}体 / {compare.first.varieties}種類</p><p>厳選完了 {compare.first.fruit.complete}体</p></div><div><b>{state.accounts.find(a=>a.id===second)?.name}</b><p>所持 {compare.second.individuals}体 / {compare.second.varieties}種類</p><p>厳選完了 {compare.second.fruit.complete}体</p></div></div><div className="overview"><div>共通する所持種類 <span>{compare.common.length}</span></div><div>現在のアカウントのみ <span>{compare.firstOnly.length}</span></div><div>比較先のみ <span>{compare.secondOnly.length}</span></div></div><div className="button-row"><button className="secondary" onClick={()=>selectOwned(undefined,compare.common)}>共通キャラを表示</button><button className="secondary" onClick={()=>selectOwned(undefined,compare.firstOnly)}>現在のアカウント限定を表示</button></div><p className="hint">比較はキャラクターIDの集合で行います。個体数の多重カウントはしません。</p></>:<p className="hint">比較にはゲームアカウントが2つ以上必要です。</p>}</Panel>
 </div>;
}
