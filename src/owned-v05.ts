import type { AppState, FruitSlot, OwnedCharacter, OwnedHistory } from './types';

export const FRUIT_NAMES = ['未設定','同族の絆・加撃','同族の絆・加命','同族の絆・加速','同族の絆・加命撃','同族の絆・加撃速','同族の絆・加速命','撃種の絆・加撃','撃種の絆・加命','撃種の絆・加速','戦型の絆・加撃','戦型の絆・加命','戦型の絆・加速','熱き友撃','速必殺','将命削り','兵命削り','学び','スコア稼ぎ','Sランク','ちび癒し','ケガ減り','毒がまん','一撃失心','ハート強化','その他'];
export const FRUIT_GRADES = ['未設定','1級','1級M','1級L','特級','特級M','特級L','特級EL','特L','特M','特EL'];
export const SOUL_SKILLS = ['対火の心得','対水の心得','対木の心得','対光の心得','対闇の心得','対弱の心得','対将の心得','対兵の心得','窮地の活路','不屈の闘力','不屈の防御','不屈の速度','収檻回避','精神力','鎖縛回避','伝染抵抗','HWマスター','NP耐性','火柱耐性','ゲージ必中','変身回復'];
const blank = ():FruitSlot=>({name:'未設定',grade:'未設定'});
export function legacyFruit(value:string):FruitSlot {
 const s=String(value||'').trim(); if(!s)return blank();
 const grade=FRUIT_GRADES.slice(1).sort((a,b)=>b.length-a.length).find(g=>s.endsWith(' '+g));
 return {name:grade?s.slice(0,-grade.length-1):s,grade:grade??'未設定'};
}
export function fruitLabel(v:FruitSlot):string {return v.name==='未設定'?'':`${v.name}${v.grade==='未設定'?'':' '+v.grade}`;}
export function normalizeOwned(o:OwnedCharacter):OwnedCharacter {
 // Legacy fruit strings remain unchanged; optional v0.5 fields are filled only for display/edit.
 const slots=Array.isArray(o.fruitSlots)?o.fruitSlots:Array.isArray(o.fruits)?o.fruits.map(legacyFruit):[];
 const targets=Array.isArray(o.fruitTargets)?o.fruitTargets:Array.isArray(o.targetFruits)?o.targetFruits.map(legacyFruit):[];
 return {...o,fruitSlots:slots.map(x=>({name:x.name||'未設定',grade:x.grade||'未設定'})),fruitTargets:targets.map(x=>({name:x.name||'未設定',grade:x.grade||'未設定'})),plusValues:o.plusValues??{hp:0,attack:0,speed:0},trainingStatus:o.trainingStatus??'未育成',heroBook:o.heroBook??false,favorite:o.favorite??false,tags:o.tags??[],history:o.history??[]};
}
export function fruitProgress(o:OwnedCharacter):{met:number;total:number;percent:number;complete:boolean} {
 const x=normalizeOwned(o);const goals=(x.fruitTargets??[]).filter(f=>f.name!=='未設定');
 if(!goals.length)return {met:o.completed?1:0,total:0,percent:o.completed?100:0,complete:!!o.completed};
 const available=[...(x.fruitSlots??[])];let met=0;
 for(const goal of goals){const i=available.findIndex(item=>item.name===goal.name&&(goal.grade==='未設定'||item.grade===goal.grade));if(i!==-1){met++;available.splice(i,1);}}
 return {met,total:goals.length,percent:Math.round(100*met/goals.length),complete:met===goals.length};
}
export function updateFruitSlot(o:OwnedCharacter,which:'fruitSlots'|'fruitTargets',index:number,slot:FruitSlot):OwnedCharacter {
 const x=normalizeOwned(o);const list=[...(x[which]??[])];
 if(index<0||index>=4)throw Error('スロット番号が不正です');
 while(list.length<=index)list.push(blank());list[index]=slot;
 const updated={...x,[which]:list};
 return {...updated,fruits:(updated.fruitSlots??[]).map(fruitLabel).filter(Boolean),targetFruits:(updated.fruitTargets??[]).map(fruitLabel).filter(Boolean),completed:fruitProgress(updated).complete};
}
export function appendHistory(o:OwnedCharacter,action:string,detail:string,id:string,at:string):OwnedCharacter {
 const entry:OwnedHistory={id,at,action,detail};
 return {...o,updatedAt:at,history:[...(o.history??[]),entry].slice(-40)};
}
export type BulkPatch={favorite?:boolean;trainingStatus?:NonNullable<OwnedCharacter['trainingStatus']>;tag?:string};
export function bulkUpdate(state:AppState,ids:string[],patch:BulkPatch,idMaker:()=>string,at:string):AppState {
 const selection=new Set(ids);return {...state,owned:state.owned.map(item=>{
  if(!selection.has(item.id))return item;
  const o=normalizeOwned(item);const tags=patch.tag?.trim()?Array.from(new Set([...(o.tags??[]),patch.tag.trim()])):o.tags;
  return appendHistory({...o,...(patch.favorite===undefined?{}:{favorite:patch.favorite}),...(patch.trainingStatus?{trainingStatus:patch.trainingStatus}:{}),tags},'一括編集','お気に入り・育成状態・タグ更新',idMaker(),at);
 })};
}
