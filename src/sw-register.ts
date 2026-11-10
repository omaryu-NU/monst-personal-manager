export function registerOfflineShell(){
 if(!('serviceWorker' in navigator)||!import.meta.env.PROD)return;
 window.addEventListener('load',()=>{void navigator.serviceWorker.register('/sw.js').then(reg=>{
  const notify=()=>{if(reg.waiting&&navigator.serviceWorker.controller)window.dispatchEvent(new CustomEvent('monst:update-ready',{detail:reg.waiting}));};
  notify();reg.addEventListener('updatefound',()=>{const w=reg.installing;w?.addEventListener('statechange',()=>{if(w.state==='installed')notify()})});
  let controlled=Boolean(navigator.serviceWorker.controller);navigator.serviceWorker.addEventListener('controllerchange',()=>{if(controlled)window.location.reload();controlled=true});
 }).catch(console.warn)});
}
