(()=>{
function poolForLocation(pathname, search=''){
 const match=pathname.match(/^\/(lod|classic)(?:\/|$)/);
 return match?match[1]:new URLSearchParams(search).get('pool')==='lod'?'lod':'classic';
}
function ladderUrl(pool, values={}){
 const query=new URLSearchParams();
 for(const key of ['q','sort','dir','page','player','match']){
  const value=values[key];
  if(value==null||value===''||(key==='sort'&&value==='rank')||(key==='dir'&&value==='asc')||(key==='page'&&Number(value)<=1))continue;
  query.set(key,String(value));
 }
 return '/'+(pool==='lod'?'lod':'classic')+'/'+(query.size?'?'+query:'');
}
function legacyLadderTarget(search){
 const values=new URLSearchParams(search);
 if(!['pool','mode','q','sort','dir','page','player','match'].some(key=>values.has(key)))return null;
 return ladderUrl(poolForLocation('/',search),Object.fromEntries(values));
}

const legacyTarget=legacyLadderTarget(location.search);
if(legacyTarget)location.replace(legacyTarget+location.hash);

})();
