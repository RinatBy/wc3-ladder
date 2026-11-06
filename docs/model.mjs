export function selectPlayers(players, options={}) {
  const term=String(options.term??'').trim().toLocaleLowerCase();
  const sort=['rank','level','clan','name','mmr','xp','wins','losses','appearances','rated_games'].includes(options.sort)?options.sort:'rank';
  const direction=options.dir==='desc'?-1:1;
  const size=Math.max(1,Math.min(100,Math.trunc(Number(options.size)||20)));
  const selected=players.filter(p=>!term||String(p.name).toLocaleLowerCase().includes(term));
  selected.sort((a,b)=>{
    const left=a[sort],right=b[sort];
    if (!['name','clan'].includes(sort)) {
      if (left==null && right!=null) return 1;
      if (left!=null && right==null) return -1;
    }
    const delta=['name','clan'].includes(sort)?String(left??'').localeCompare(String(right??''),'ru'):(Number(left)||0)-(Number(right)||0);
    return direction*delta||(Number(a.rank)||0)-(Number(b.rank)||0)||String(a.name).localeCompare(String(b.name));
  });
  const pages=Math.max(1,Math.ceil(selected.length/size));
  const page=Math.max(1,Math.min(pages,Math.trunc(Number(options.page)||1)));
  return {rows:selected.slice((page-1)*size,page*size),page,pages,total:selected.length};
}
export function playerProfile(players,name) {
  return players.find(p=>p.name.toLocaleLowerCase()===String(name).toLocaleLowerCase())??null;
}
