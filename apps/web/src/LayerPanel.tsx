export type ReferenceSettings={rivers:boolean;borders:boolean;grid:boolean;texture:boolean;mini:boolean};
export type LayerItem={id:string;label:string;checked:boolean;onChange:(v:boolean)=>void;suppressed?:string};
export default function LayerPanel({items,onClose,onReset,collection,onCollection}:{items:LayerItem[];onClose:()=>void;onReset:()=>void;collection:'historical'|'modern';onCollection:(v:'historical'|'modern')=>void}){
 return <aside className="encyclopedia floating-panel layer-panel" aria-label="إدارة الطبقات"><button className="panel-close" aria-label="إغلاق الطبقات" onClick={onClose}>×</button><h2>إدارة الطبقات</h2><p className="muted">تتحكم هذه اللوحة في الطبقات نفسها المستخدمة في أدوات الاستكشاف. قد يحجب الزمن أو الحقبة طبقة مفعلة.</p>
 {items.map(item=><label key={item.id} className="central-layer"><input aria-label={item.label} type="checkbox" checked={item.checked} onChange={e=>item.onChange(e.target.checked)}/><span>{item.label}{item.checked&&item.suppressed&&<small>{item.suppressed}</small>}</span></label>)}
 <label>مجموعة المعجم في الخريطة<select aria-label="مجموعة المعجم المركزية" value={collection} onChange={e=>onCollection(e.target.value as 'historical'|'modern')}><option value="historical">التاريخية</option><option value="modern">المعاصرة</option></select></label>
 <button onClick={onReset}>استعادة الطبقات الافتراضية</button></aside>;
}
