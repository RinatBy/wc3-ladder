(()=>{
function selectPlayers(players, options={}) {
  const term=String(options.term??'').trim().toLocaleLowerCase();
  const sort=['rank','level','clan','name','xp','wins','losses','appearances'].includes(options.sort)?options.sort:'rank';
  const direction=options.dir==='desc'?-1:1;
  const size=Math.max(1,Math.min(100,Math.trunc(Number(options.size)||20)));
  const selected=players.filter(p=>!term||String(p.name).toLocaleLowerCase().includes(term));
  selected.sort((a,b)=>{
    const left=a[sort],right=b[sort];
    const delta=['name','clan'].includes(sort)?String(left??'').localeCompare(String(right??''),'ru'):(Number(left)||0)-(Number(right)||0);
    return direction*delta||(Number(a.rank)||0)-(Number(b.rank)||0)||String(a.name).localeCompare(String(b.name));
  });
  const pages=Math.max(1,Math.ceil(selected.length/size));
  const page=Math.max(1,Math.min(pages,Math.trunc(Number(options.page)||1)));
  return {rows:selected.slice((page-1)*size,page*size),page,pages,total:selected.length};
}
function playerProfile(players,name) {
  return players.find(p=>p.name.toLocaleLowerCase()===String(name).toLocaleLowerCase())??null;
}

const $=id=>document.getElementById(id);
const params=new URLSearchParams(location.search);
const pool=params.get('pool')==='lod'?'lod':'classic';
const mode=params.get('mode')==='archive'?'archive':'live';
let term=params.get('q')??'',sort=params.get('sort')??'rank',dir=params.get('dir')??'asc',page=Number(params.get('page'))||1;
const archived=JSON.parse($('archive-data').textContent);
let rankings=JSON.parse($('rankings-data').textContent);
const format=value=>Number.isFinite(value)?value.toLocaleString('ru-RU'):'—';
function url(changes={}){const p=new URLSearchParams({pool,mode,q:term,sort,dir,page:String(page)});for(const[k,v]of Object.entries(changes)){if(v==null)p.delete(k);else p.set(k,String(v));}return 'index.html?'+p;}
function node(tag,text,className){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(className)n.className=className;return n;}
function activePlayers(){return mode==='archive'?archived.players:(rankings.pools?.[pool]?.players??[]);}
function linkPlayer(p){const a=node('a',p.name);a.href=url({player:p.name});return a;}
function row(p){
 const tr=document.createElement('tr');tr.append(node('td',p.rank??'—'));
 const level=node('td');
 if(Number.isFinite(p.level)&&Number.isFinite(p.progress)){
  const bar=node('div',null,'level-bar');const fill=node('div',null,'level-fill');fill.style.width=Math.max(0,Math.min(100,p.progress))+'%';bar.append(fill,node('span',p.level,'level-value'));bar.setAttribute('aria-label','Уровень '+p.level+', прогресс '+p.progress+'%');level.append(bar);
 }else level.textContent='—';
 tr.append(level,node('td',mode==='archive'?(p.clan||'—'):format(p.appearances)));
 const portrait=node('td');if(p.portrait){const img=node('img',null,'portrait-icon');if(/^assets\/war3\/[A-Za-z0-9_./-]+$/.test(p.portrait)&&!p.portrait.includes('..'))img.src=p.portrait;img.alt='';portrait.append(img);}else portrait.textContent='—';tr.append(portrait);
 const name=node('td',null,'player-cell');name.append(linkPlayer(p));tr.append(name,node('td',Number.isFinite(p.xp)?format(p.xp):'—'),node('td',format(p.wins)),node('td',format(p.losses)));return tr;
}
function showProfile(name){
 document.querySelector('.table-scroll').hidden=!!name;document.querySelector('.pager').hidden=!!name;$('table-state').hidden=!!name;
 const panel=$('profile');panel.replaceChildren();if(!name){panel.hidden=true;return;}
 panel.hidden=false;const p=playerProfile(activePlayers(),name);
 if(!p){const back=node('a','← К таблице');back.href=url({player:null});panel.append(node('h1','Игрок не найден'),node('p','В выбранном разделе нет записи об этом игроке.'),back);return;}
 document.title=p.name+' — Warcraft III Online';panel.append(node('h1',p.name));
 const wrap=node('div',null,'profile-layout');
 if(p.portrait&&/^assets\/war3\/[A-Za-z0-9_./-]+$/.test(p.portrait)&&!p.portrait.includes('..')){const img=node('img',null,'profile-portrait');img.src=p.portrait;img.alt='Портрет игрока';wrap.append(img);}
 const dl=node('dl',null,'profile-values');const total=Number.isFinite(p.wins)&&Number.isFinite(p.losses)?p.wins+p.losses:null;
 const values=[['Место',p.rank??'—'],['Уровень',p.level??'—'],['MMR',format(p.mmr)],['Опыт',format(p.xp)],['Победы',format(p.wins)],['Поражения',format(p.losses)],['Игр в записях бота',format(p.appearances??total)],['Процент побед',total?(100*p.wins/total).toFixed(1)+'%':'—']];
 if(mode==='archive')values.splice(2,1,['Клан',p.clan||'—']);
 if(mode!=='archive')for(const[key,label]of [['kills','Убийства'],['deaths','Смерти'],['assists','Помощь'],['creepkills','Крипы'],['towerkills','Башни']])values.push([label,format(p[key])]);
 for(const[label,value]of values)dl.append(node('dt',label),node('dd',value));
 wrap.append(dl);panel.append(wrap,node('p',mode==='archive'?'Карточка из архивной таблицы 2007 года. Подробная история матчей в этом снимке отсутствует.':p.result_games?'Предварительная статистика сервера.':'Участник сохранённых игр. Результаты этих матчей бот не записал.', 'profile-note'));
 const back=node('a','← К таблице');back.href=url({player:null});panel.append(back);
}
function render(){
 const isArchive=mode==='archive';const label=pool==='lod'?'DotA LoD':'DotA Classic';
 $('crumb').textContent=isArchive?'Lordaeron · Solo · 2007':label;
 $('classic-link').setAttribute('aria-current',!isArchive&&pool==='classic'?'page':'false');$('lod-link').setAttribute('aria-current',!isArchive&&pool==='lod'?'page':'false');$('archive-link').setAttribute('aria-current',isArchive?'page':'false');
 $('portrait-heading').textContent=isArchive?'Раса':'Герой';
 $('clan-heading').textContent=isArchive?'Клан':'Игр';$('clan-heading').dataset.sort=isArchive?'clan':'appearances';
 $('notice-title').textContent=isArchive?'ОБРАЗЕЦ ОФОРМЛЕНИЯ · 2007':label.toUpperCase();
 $('notice-text').textContent=isArchive?'Имена и результаты взяты из оригинальной архивной страницы. Это не статистика нашего сервера.':rankings.status==='not_connected'?'Источник результатов матчей ещё не подключён. Здесь будет рейтинг нашего сервера.':rankings.status==='preview'?'Предварительная статистика сервера · '+(rankings.pools?.[pool]?.completed_matches?'сохранённые результаты игр':'профили участников сохранённых игр'):pool==='classic'?'Общая статистика Classic и новогодней карты.':'Отдельная статистика LoD.';
 const selected=selectPlayers(activePlayers(),{term,sort,dir,page,size:20});page=selected.page;
 $('players').replaceChildren();for(const p of selected.rows)$('players').append(row(p));
 if(!selected.rows.length){const tr=node('tr');const td=node('td',term?'Игроки по этому запросу не найдены.':'Пока нет записей зачтённых матчей.', 'empty-cell');td.colSpan=8;tr.append(td);$('players').append(tr);}
 $('table-state').textContent=(isArchive?'Исторические данные · ':'')+selected.total+' игроков · страница '+page+' из '+selected.pages;
 $('page-list').replaceChildren();for(let i=1;i<=selected.pages;i++){if(i===page)$('page-list').append(node('span',i));else{const b=node('button',i);b.type='button';b.addEventListener('click',()=>{page=i;render();});$('page-list').append(b);}}
 $('first-page').disabled=$('previous-page').disabled=page<=1;$('next-page').disabled=$('last-page').disabled=page>=selected.pages;
 $('first-page').onclick=()=>{page=1;render();};$('previous-page').onclick=()=>{page--;render();};$('next-page').onclick=()=>{page++;render();};$('last-page').onclick=()=>{page=selected.pages;render();};
 for(const b of document.querySelectorAll('[data-sort]')){b.closest('th').setAttribute('aria-sort',b.dataset.sort===sort?(dir==='asc'?'ascending':'descending'):'none');}
 showProfile(params.get('player'));
}
$('player-search').value=term;
$('search-form').addEventListener('submit',e=>{e.preventDefault();term=$('player-search').value.trim();page=1;render();});
for(const b of document.querySelectorAll('[data-sort]'))b.addEventListener('click',()=>{dir=sort===b.dataset.sort&&dir==='asc'?'desc':'asc';sort=b.dataset.sort;page=1;render();});
render();
if(location.protocol==='http:'||location.protocol==='https:')fetch('data/rankings.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();}).then(data=>{if(data.schema_version!==1||!data.pools)throw Error('Unsupported data');rankings=data;render();}).catch(()=>{if(mode==='live')$('notice-text').textContent=(rankings.status==='preview'?'Предварительная статистика · ':'')+'Не удалось обновить данные. Показана сохранённая копия.';});

})();
