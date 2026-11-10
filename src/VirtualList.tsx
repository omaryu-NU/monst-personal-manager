import {useState,useEffect,useRef,type ReactNode} from 'react';
/** Fixed-height, measured-width window. Render stable item IDs; without JS it degrades to an empty viewport, never mutates stored data. */
export default function VirtualList<T>({items,keyFor,renderItem,estimateHeight=210,minWidth=270,overscan=3,ariaLabel}:{items:T[];keyFor:(item:T)=>string;renderItem:(item:T)=>ReactNode;estimateHeight?:number;minWidth?:number;overscan?:number;ariaLabel:string}){
 const host=useRef<HTMLDivElement>(null); const [scroll,setScroll]=useState(0);const [width,setWidth]=useState(850);const [height,setHeight]=useState(620);
 useEffect(()=>{const h=host.current;if(!h)return;const ob=new ResizeObserver(()=>{setWidth(h.clientWidth);setHeight(h.clientHeight)});ob.observe(h);setWidth(h.clientWidth);setHeight(h.clientHeight);return()=>ob.disconnect();},[]);
 useEffect(()=>{if(host.current)host.current.scrollTop=0;setScroll(0);},[items]);
 const columns=Math.max(1,Math.floor(width/minWidth));const rows=Math.ceil(items.length/columns);const start=Math.max(0,Math.floor(scroll/estimateHeight)-overscan);const end=Math.min(rows,Math.ceil((scroll+height)/estimateHeight)+overscan);const visible=items.slice(start*columns,end*columns);
 return <div ref={host} role="region" aria-label={ariaLabel} tabIndex={0} className="v09-virtual" onScroll={e=>setScroll(e.currentTarget.scrollTop)}><div style={{height:rows*estimateHeight,position:'relative'}}><div style={{position:'absolute',top:start*estimateHeight,left:0,right:0,display:'grid',gridTemplateColumns:`repeat(${columns},minmax(0,1fr))`,gridAutoRows:`${estimateHeight}px`,gap:0}}>{visible.map(item=><div key={keyFor(item)} className="v09-cell">{renderItem(item)}</div>)}</div></div></div>;
}
