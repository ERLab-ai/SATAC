// Static original vector assets extracted from baseline/v0.13 src/atlas.html (667dfd73340d9b9161bdd7b448f2fa36bb385c3e). No legacy script executed.
export const eraLabels:Record<string,string>={"all":"كل العصور","deep":"ذاكرة الإنسان","ancient":"العصور القديمة","islamic":"العصور الإسلامية","states":"الدول السعودية","modern":"المملكة والعالم"};
export const thematicEras=Object.keys(eraLabels);
const categoryFiles:Record<string,string>={"الآثار":"category-0","الحضارات":"category-1","عبر القارات":"category-2","الجغرافيا":"category-3","الأحداث":"category-4","الحج":"category-5","الدولة السعودية":"category-6","الواحات":"category-7","المنشآت الحجرية":"category-8","هندسة المياه":"category-9","العمران الريفي":"category-10","الطبيعة":"category-11","التراث الصناعي":"category-12"};
const artNames=new Set(["tomb","rock","oasis","port","route","fort","globe","dam","terrace","dune","industry"]);
export function artwork(name:string){return '/legacy-art/'+(artNames.has(name)?name:'globe')+'.svg';}
export function categoryIcon(category:string){const name=categoryFiles[category];return name?'/legacy-art/'+name+'.svg':null;}
export function sourceEraAllows(collection:'historical'|'modern',theme:string){return theme==='all'||(collection==='historical'?theme==='islamic':theme==='modern');}
