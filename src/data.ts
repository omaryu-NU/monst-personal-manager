import type { AppState, Character } from './types';
export const DEMO_CATALOG: Character[] = [
 {id:'demo-1',name:'サンプル騎士',attribute:'火',abilities:['アンチ重力バリア','アンチダメージウォール'],type:'反射',style:'バランス型',race:'聖騎士'},
 {id:'demo-2',name:'サンプル魔導士',attribute:'水',abilities:['マインスイーパー','アンチワープ'],type:'貫通',style:'砲撃型',race:'魔族'},
 {id:'demo-3',name:'サンプル守護者',attribute:'木',abilities:['アンチ魔法陣'],type:'反射',style:'パワー型',race:'ロボット'},
 {id:'demo-4',name:'サンプル旅人',attribute:'光',abilities:['アンチ転送壁','アンチ減速壁'],type:'貫通',style:'スピード型',race:'亜人'},
 {id:'demo-5',name:'サンプル忍者',attribute:'闇',abilities:['アンチブロック','アンチワープ'],type:'反射',style:'バランス型',race:'亜人'},
];
export const initialState = (): AppState => ({schemaVersion:1,catalog:DEMO_CATALOG,accounts:[{id:'main',name:'メイン'}],activeAccountId:'main',owned:[],teams:[],quests:[],todos:[],runs:[],bonds:[],events:[],playLogs:[]});
export const makeId = () => crypto.randomUUID();
