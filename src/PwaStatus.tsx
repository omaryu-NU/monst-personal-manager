import {useEffect,useState} from 'react';
interface InstallEvent extends Event {prompt:()=>Promise<void>;userChoice:Promise<{outcome:string}>}
export default function PwaStatus({safeToUpdate}:{safeToUpdate:boolean}){const [install,setInstall]=useState<InstallEvent|null>(null);const [update,setUpdate]=useState<ServiceWorker|null>(null);
 useEffect(()=>{const onInstall=(e:Event)=>{e.preventDefault();setInstall(e as InstallEvent)};const onUpdate=(e:Event)=>setUpdate((e as CustomEvent<ServiceWorker>).detail);window.addEventListener('beforeinstallprompt',onInstall);window.addEventListener('monst:update-ready',onUpdate);return()=>{window.removeEventListener('beforeinstallprompt',onInstall);window.removeEventListener('monst:update-ready',onUpdate)}},[]);
 if(!install&&!update)return null;
 return <section className="v09-pwa-banner" role="status">{update?<><b>新バージョンを利用できます</b><span>編集内容の同期が完了したことを確認してから更新してください。</span><button disabled={!safeToUpdate} title={!safeToUpdate?'未同期の変更があります。先に同期してください':undefined} onClick={()=>update.postMessage({type:'SKIP_WAITING'})}>更新して再読み込み</button></>:<><b>アプリをホーム画面に追加</b><span>対応ブラウザでアプリのように起動できます。</span><button onClick={()=>{void install?.prompt().then(()=>setInstall(null))}}>インストール</button></>}</section>;
}
