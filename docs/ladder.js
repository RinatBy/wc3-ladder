(()=>{
const HERO_PORTRAITS={
  "abaddon": "assets/heroes/gajd-po-abadonu.png",
  "admiral": "assets/heroes/gajd-po-kunka.png",
  "aggron stonebreak": "assets/heroes/gajd-po-ogr-magu.png",
  "aiushtha": "assets/heroes/gajd-po-koze.png",
  "akasha": "assets/heroes/gajd-po-akashe.png",
  "alchemist": "assets/heroes/gajd-po-alximiku.png",
  "alleria": "assets/heroes/gajd-po-vinde.png",
  "ancient apparition": "assets/heroes/gajd-po-apparatu.png",
  "anti-mage": "assets/heroes/gajd-po-magine.png",
  "anub'arak": "assets/heroes/gajd-po-anubaraku.png",
  "anub'seran": "assets/heroes/gajd-po-nerubu.png",
  "anubarak": "assets/heroes/gajd-po-anubaraku.png",
  "arc warden": "assets/heroes/gajd-po-zetu.png",
  "atropos": "assets/heroes/gajd-po-atroposu.png",
  "aurel vlaicu": "assets/heroes/gajd-po-vertoletu.png",
  "axe": "assets/heroes/gajd-po-aksu.png",
  "azgalor": "assets/heroes/gajd-po-pit-lordu.png",
  "azwraith": "assets/heroes/gajd-po-fantom-lanseru.png",
  "balanar": "assets/heroes/gajd-po-balanaru.png",
  "bane elemental": "assets/heroes/gajd-po-atroposu.png",
  "banehallow": "assets/heroes/gajd-po-likanu.png",
  "barathrum": "assets/heroes/gajd-po-bare.png",
  "batrider": "assets/heroes/gajd-po-betrajderu.png",
  "beastmaster": "assets/heroes/gajd-po-reksaru.png",
  "black arachnia": "assets/heroes/gajd-na-brudmazer.png",
  "bloodrune": "assets/heroes/gajd-po-geomanseru.png",
  "bloodseeker": "assets/heroes/gajd-po-bludsikeru.png",
  "bone fletcher": "assets/heroes/gajd-po-bone.png",
  "bounty hunter": "assets/heroes/gajd-po-gondaru.png",
  "boush": "assets/heroes/gajd-po-tinkeru.png",
  "bradwarden": "assets/heroes/gajd-po-kentavru.png",
  "brewmaster": "assets/heroes/gajd-po-pande.png",
  "bristleback": "assets/heroes/gajd-po-kabanu.png",
  "broodmother": "assets/heroes/gajd-na-brudmazer.png",
  "butcher": "assets/heroes/gajd-po-pudzhu.png",
  "cairne bloodhoof": "assets/heroes/gajd-po-taurenu.png",
  "centaur": "assets/heroes/gajd-po-kentavru.png",
  "centaur warchief": "assets/heroes/gajd-po-kentavru.png",
  "chaos knight": "assets/heroes/gajd-po-nessayu.png",
  "chen": "assets/heroes/gajd-po-chenu.png",
  "clinkz": "assets/heroes/gajd-po-bone.png",
  "clockwerk": "assets/heroes/gajd-po-kloku.png",
  "clockwerk goblin": "assets/heroes/gajd-po-kloku.png",
  "crixalis": "assets/heroes/gajd-po-skorpionu.png",
  "crystal maiden": "assets/heroes/gajd-po-rilaj.png",
  "darchrow": "assets/heroes/gajd-po-enigme.png",
  "dark seer": "assets/heroes/gajd-po-dark-siru.png",
  "darkterror": "assets/heroes/gajd-po-vojdu.png",
  "davion": "assets/heroes/gajd-po-dragon-knajt.png",
  "dazzle": "assets/heroes/gajd-po-dazzlu.png",
  "death prophet": "assets/heroes/gajd-po-krobelus.png",
  "demnok lannik": "assets/heroes/gajd-po-varloku.png",
  "demon witch": "assets/heroes/gajd-po-lionu.png",
  "dirge": "assets/heroes/gajd-po-zombi.png",
  "disruptor": "assets/heroes/gajd-po-trallu.png",
  "doom": "assets/heroes/gajd-po-lyuciferu.png",
  "doom bringer": "assets/heroes/gajd-po-lyuciferu.png",
  "dragon knight": "assets/heroes/gajd-po-dragon-knajt.png",
  "dragonus": "assets/heroes/gajd-po-skaj-magu.png",
  "drow ranger": "assets/heroes/gajd-po-trakse.png",
  "dwarven sniper": "assets/heroes/gajd-po-snajperu.png",
  "earth spirit": "assets/heroes/gajd-po-kaolinu.png",
  "earthshaker": "assets/heroes/gajd-po-shejkeru.png",
  "ember spirit": "assets/heroes/gajd-po-ksinu.png",
  "enchantress": "assets/heroes/gajd-po-koze.png",
  "enigma": "assets/heroes/gajd-po-enigme.png",
  "eredar": "assets/heroes/gajd-po-eredaru.png",
  "ezalor": "assets/heroes/gajd-po-ezaloru.png",
  "faceless void": "assets/heroes/gajd-po-vojdu.png",
  "faerie dragon": "assets/heroes/gajd-po-paku.png",
  "fire panda": "assets/heroes/gajd-po-magine.png",
  "flesh golem": "assets/heroes/gajd-po-zombi.png",
  "furion": "assets/heroes/gajd-po-furionu.png",
  "geomancer": "assets/heroes/gajd-po-geomanseru.png",
  "goblin shredder": "assets/heroes/gajd-po-rezaku.png",
  "goblin techies": "assets/heroes/gajd-po-mineru.png",
  "gondar": "assets/heroes/gajd-po-gondaru.png",
  "gorgon": "assets/heroes/gajd-po-meduze.png",
  "grand magus": "assets/heroes/gajd-po-rubiku.png",
  "guardian wisp": "assets/heroes/gajd-po-vispu.png",
  "gyrocopter": "assets/heroes/gajd-po-vertoletu.png",
  "harbinger": "assets/heroes/gajd-po-destroeru.png",
  "holy knight": "assets/heroes/gajd-po-chenu.png",
  "huskar": "assets/heroes/gajd-po-xuskaru.png",
  "icarus": "assets/heroes/gajd-po-feniksu.png",
  "invoker": "assets/heroes/gajd-po-invokeru.png",
  "io": "assets/heroes/gajd-po-vispu.png",
  "ish'kafel": "assets/heroes/gajd-po-dark-siru.png",
  "jah'rakal": "assets/heroes/gajd-po-trolyu.png",
  "jakiro": "assets/heroes/gajd-po-dzhakiro.png",
  "jin'zakk": "assets/heroes/gajd-po-betrajderu.png",
  "juggernaut": "assets/heroes/gajd-po-yurnero.png",
  "kaldr": "assets/heroes/gajd-po-apparatu.png",
  "kaolin": "assets/heroes/gajd-po-kaolinu.png",
  "kardel sharpeye": "assets/heroes/gajd-po-snajperu.png",
  "keeper of the light": "assets/heroes/gajd-po-ezaloru.png",
  "keeper of the light 2": "assets/heroes/gajd-po-ezaloru.png",
  "keeper of the light 3": "assets/heroes/gajd-po-ezaloru.png",
  "kel'thuzad": "assets/heroes/gajd-po-lichu.png",
  "krobelus": "assets/heroes/gajd-po-krobelus.png",
  "kunkka": "assets/heroes/gajd-po-kunka.png",
  "lanaya": "assets/heroes/gajd-po-lanai.png",
  "legion commander": "assets/heroes/gajd-po-legionu.png",
  "leoric": "assets/heroes/gajd-po-leoriku.png",
  "lesale deathbringer": "assets/heroes/gajd-po-venomanseru.png",
  "leshrac": "assets/heroes/gajd-po-leshraku.png",
  "leviathan": "assets/heroes/gajd-po-tajdu.png",
  "lich": "assets/heroes/gajd-po-lichu.png",
  "lifestealer": "assets/heroes/gajd-po-naiksu-gulya.png",
  "lightning revenant": "assets/heroes/gajd-po-razoru.png",
  "lina": "assets/heroes/gajd-po-line.png",
  "lina inverse": "assets/heroes/gajd-po-line.png",
  "lion": "assets/heroes/gajd-po-lionu.png",
  "lone druid": "assets/heroes/gajd-po-medvedyu.png",
  "lone druid bear form": "assets/heroes/gajd-po-medvedyu.png",
  "lord of avernus": "assets/heroes/gajd-po-abadonu.png",
  "lord of olympia": "assets/heroes/gajd-po-zevsu.png",
  "lord of olympus": "assets/heroes/gajd-po-zevsu.png",
  "lucifer": "assets/heroes/gajd-po-lyuciferu.png",
  "luna": "assets/heroes/gajd-po-lune.png",
  "luna moonfang": "assets/heroes/gajd-po-lune.png",
  "lycanthrope": "assets/heroes/gajd-po-likanu.png",
  "magina": "assets/heroes/gajd-po-magine.png",
  "magnataur": "assets/heroes/gajd-po-magnusu.png",
  "magnus": "assets/heroes/gajd-po-magnusu.png",
  "mangix": "assets/heroes/gajd-po-pande.png",
  "medusa": "assets/heroes/gajd-po-meduze.png",
  "meepo": "assets/heroes/gajd-po-geomanseru.png",
  "mercurial": "assets/heroes/gajd-na-spektru.png",
  "miner": "assets/heroes/gajd-po-mineru.png",
  "mirana": "assets/heroes/gajd-po-mirane.png",
  "mirana nightshade": "assets/heroes/gajd-po-mirane.png",
  "mogul kahn": "assets/heroes/gajd-po-aksu.png",
  "moon rider": "assets/heroes/gajd-po-lune.png",
  "morphling": "assets/heroes/gajd-po-morfu.png",
  "morted": "assets/heroes/gajd-po-morte.png",
  "mortred": "assets/heroes/gajd-po-morte.png",
  "murloc nightcrawler": "assets/heroes/gajd-po-slarku.png",
  "n'aix": "assets/heroes/gajd-po-naiksu-gulya.png",
  "naga siren": "assets/heroes/gajd-po-nage.png",
  "naix": "assets/heroes/gajd-po-naiksu-gulya.png",
  "necro'lic": "assets/heroes/gajd-po-vizazhu.png",
  "necrolyte": "assets/heroes/gajd-po-nekrolitu.png",
  "nerif": "assets/heroes/gajd-po-oraklu.png",
  "nerubian assassin": "assets/heroes/gajd-po-anubaraku.png",
  "nerubian weaver": "assets/heroes/gajd-po-nerubu.png",
  "nessaj": "assets/heroes/gajd-po-nessayu.png",
  "netherdrake": "assets/heroes/gajd-po-vajperu.png",
  "nevermore": "assets/heroes/gajd-po-neveru.png",
  "night stalker": "assets/heroes/gajd-po-balanaru.png",
  "nortrom": "assets/heroes/gajd-po-nortu.png",
  "oblivion": "assets/heroes/gajd-po-pugne.png",
  "obsidian destroyer": "assets/heroes/gajd-po-destroeru.png",
  "ogre mage": "assets/heroes/gajd-po-ogr-magu.png",
  "ogre magi": "assets/heroes/gajd-po-ogr-magu.png",
  "omniknight": "assets/heroes/gajd-po-omniku.png",
  "oracle": "assets/heroes/gajd-po-oraklu.png",
  "panda": "assets/heroes/gajd-po-pande.png",
  "pandaren brewmaster": "assets/heroes/gajd-po-pande.png",
  "phantom assassin": "assets/heroes/gajd-po-morte.png",
  "phantom lancer": "assets/heroes/gajd-po-fantom-lanseru.png",
  "phoenix": "assets/heroes/gajd-po-feniksu.png",
  "pit lord": "assets/heroes/gajd-po-pit-lordu.png",
  "priestess of the moon": "assets/heroes/gajd-po-mirane.png",
  "prophet": "assets/heroes/gajd-po-furionu.png",
  "puck": "assets/heroes/gajd-po-paku.png",
  "pudge": "assets/heroes/gajd-po-pudzhu.png",
  "pugna": "assets/heroes/gajd-po-pugne.png",
  "purist thunderwrath": "assets/heroes/gajd-po-omniku.png",
  "queen of pain": "assets/heroes/gajd-po-akashe.png",
  "raigor stonehoof": "assets/heroes/gajd-po-shejkeru.png",
  "raijin thunderkeg": "assets/heroes/gajd-po-shtormu.png",
  "rasta": "assets/heroes/gajd-po-raste.png",
  "rattletrap": "assets/heroes/gajd-po-kloku.png",
  "razor": "assets/heroes/gajd-po-razoru.png",
  "razzil darkbrew": "assets/heroes/gajd-po-alximiku.png",
  "rexxar": "assets/heroes/gajd-po-reksaru.png",
  "rhasta": "assets/heroes/gajd-po-raste.png",
  "rigwarl": "assets/heroes/gajd-po-kabanu.png",
  "rikimaru": "assets/heroes/gajd-po-rikimaru.png",
  "rizzrak": "assets/heroes/gajd-po-rezaku.png",
  "rogue knight": "assets/heroes/gajd-po-svenu.png",
  "roof": "assets/heroes/gajd-po-derevu-rufu.png",
  "rooftrellen": "assets/heroes/gajd-po-derevu-rufu.png",
  "rotund'jere": "assets/heroes/gajd-po-nekrolitu.png",
  "rubick": "assets/heroes/gajd-po-rubiku.png",
  "rylai": "assets/heroes/gajd-po-rilaj.png",
  "sacred warrior": "assets/heroes/gajd-po-xuskaru.png",
  "sand king": "assets/heroes/gajd-po-skorpionu.png",
  "shadow demon": "assets/heroes/gajd-po-eredaru.png",
  "shadow fiend": "assets/heroes/gajd-po-neveru.png",
  "shadow priest": "assets/heroes/gajd-po-dazzlu.png",
  "shadow shaman": "assets/heroes/gajd-po-raste.png",
  "shendelzare silkwood": "assets/heroes/gajd-na-vengu.png",
  "silencer": "assets/heroes/gajd-po-nortu.png",
  "skeleton king": "assets/heroes/gajd-po-leoriku.png",
  "skywrath mage": "assets/heroes/gajd-po-skaj-magu.png",
  "slardar": "assets/heroes/gajd-pod-slardaru.png",
  "slark": "assets/heroes/gajd-po-slarku.png",
  "slayer": "assets/heroes/gajd-po-line.png",
  "slithereen guard": "assets/heroes/gajd-pod-slardaru.png",
  "slithice": "assets/heroes/gajd-po-nage.png",
  "sniper": "assets/heroes/gajd-po-snajperu.png",
  "soul keeper": "assets/heroes/gajd-po-terroru.png",
  "spectre": "assets/heroes/gajd-na-spektru.png",
  "spirit breaker": "assets/heroes/gajd-po-bare.png",
  "spiritbreaker": "assets/heroes/gajd-po-bare.png",
  "stealth assassin": "assets/heroes/gajd-po-rikimaru.png",
  "stone giant": "assets/heroes/gajd-po-tini.png",
  "storm": "assets/heroes/gajd-po-shtormu.png",
  "storm spirit": "assets/heroes/gajd-po-shtormu.png",
  "storm spirit unused": "assets/heroes/gajd-po-shtormu.png",
  "strygwyr": "assets/heroes/gajd-po-bludsikeru.png",
  "sven": "assets/heroes/gajd-po-svenu.png",
  "syllabear": "assets/heroes/gajd-po-medvedyu.png",
  "tauren": "assets/heroes/gajd-po-taurenu.png",
  "tauren chieftain": "assets/heroes/gajd-po-taurenu.png",
  "techies": "assets/heroes/gajd-po-mineru.png",
  "templar assassin": "assets/heroes/gajd-po-lanai.png",
  "terrorblade": "assets/heroes/gajd-po-terroru.png",
  "thrall": "assets/heroes/gajd-po-trallu.png",
  "tidehunder": "assets/heroes/gajd-po-tajdu.png",
  "tidehunter": "assets/heroes/gajd-po-tajdu.png",
  "tinker": "assets/heroes/gajd-po-tinkeru.png",
  "tiny": "assets/heroes/gajd-po-tini.png",
  "tormented soul": "assets/heroes/gajd-po-leshraku.png",
  "traxex": "assets/heroes/gajd-po-trakse.png",
  "treant protector": "assets/heroes/gajd-po-derevu-rufu.png",
  "tresdin": "assets/heroes/gajd-po-legionu.png",
  "troll warlord": "assets/heroes/gajd-po-trolyu.png",
  "tuskarr": "assets/heroes/gajd-po-tuskaru.png",
  "twin head dragon": "assets/heroes/gajd-po-dzhakiro.png",
  "ulfsaar": "assets/heroes/gajd-po-urse.png",
  "undying": "assets/heroes/gajd-po-zombi.png",
  "ursa": "assets/heroes/gajd-po-urse.png",
  "ursa warrior": "assets/heroes/gajd-po-urse.png",
  "venga": "assets/heroes/gajd-na-vengu.png",
  "vengeful spirit": "assets/heroes/gajd-na-vengu.png",
  "venomancer": "assets/heroes/gajd-po-venomanseru.png",
  "viper": "assets/heroes/gajd-po-vajperu.png",
  "visage": "assets/heroes/gajd-po-vizazhu.png",
  "void": "assets/heroes/gajd-po-vojdu.png",
  "vol'jin": "assets/heroes/gajd-po-vich-doktoru.png",
  "warlock": "assets/heroes/gajd-po-varloku.png",
  "weaver": "assets/heroes/gajd-po-nerubu.png",
  "windrunner": "assets/heroes/gajd-po-vinde.png",
  "winter wyvern": "assets/heroes/gajd-po-vinter-vivern.png",
  "witch doctor": "assets/heroes/gajd-po-vich-doktoru.png",
  "xin": "assets/heroes/gajd-po-ksinu.png",
  "ymir": "assets/heroes/gajd-po-tuskaru.png",
  "yurnero": "assets/heroes/gajd-po-yurnero.png",
  "zet": "assets/heroes/gajd-po-zetu.png",
  "zeus": "assets/heroes/gajd-po-zevsu.png",
  "каолину": "assets/heroes/gajd-po-kaolinu.png",
  "этому герою": "assets/heroes/gajd-po-oraklu.png"
}
;
function selectPlayers(players, options={}) {
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
function playerProfile(players,name) {
  return players.find(p=>p.name.toLocaleLowerCase()===String(name).toLocaleLowerCase())??null;
}

const LADDER_PATHS = {
 classic: '/classic/',
 lod: '/lod/',
 'lod-4x4': '/lod/4x4-no-mid/',
 'lod-3x3': '/lod/3x3-only-mid/',
};
const LADDER_LABELS = {
 classic: 'DotA Classic 5×5',
 lod: 'DotA LoD 5×5',
 'lod-4x4': 'DotA LoD 4×4 · без мида',
 'lod-3x3': 'DotA LoD 3×3 · только мид',
};

function poolForLocation(pathname, search=''){
 const route=pathname.replace(/\/index\.html$/, '/').replace(/\/?$/, '/');
 const exact=Object.keys(LADDER_PATHS).find(key=>LADDER_PATHS[key]===route);
 if(exact)return exact;
 if(pathname.startsWith('/classic/'))return 'classic';
 return pathname.startsWith('/lod/')||new URLSearchParams(search).get('pool')==='lod'?'lod':'classic';
}
function ladderUrl(pool, values={}){
 const query=new URLSearchParams();
 for(const key of ['q','sort','dir','page','player','match']){
  const value=values[key];
  if(value==null||value===''||(key==='sort'&&value==='rank')||(key==='dir'&&value==='asc')||(key==='page'&&Number(value)<=1))continue;
  query.set(key,String(value));
 }
 return (Object.hasOwn(LADDER_PATHS,pool)?LADDER_PATHS[pool]:LADDER_PATHS.classic)+(query.size?'?'+query:'');
}
function legacyLadderTarget(search){
 const values=new URLSearchParams(search);
 if(!['pool','mode','q','sort','dir','page','player','match'].some(key=>values.has(key)))return null;
 return ladderUrl(poolForLocation('/',search),Object.fromEntries(values));
}

function findMatch(data,id){return (data?.matches||[]).find(m=>m.id===id)||null;}
function recentMatches(data,name){
 const player=(data?.players||[]).find(p=>p.name.toLocaleLowerCase()===String(name).toLocaleLowerCase());
 return [...new Set(player?.recent_match_ids||[])].slice(0,10).map(id=>findMatch(data,id)).filter(Boolean);
}

function matchDate(value){
 if(!value)return '—';const date=new Date(value.replace(' ','T')+(/Z$|[+-]\d\d:\d\d$/.test(value)?'':'Z'));
 return Number.isNaN(date.getTime())?'—':date.toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
}
function matchDuration(seconds){return Number.isFinite(seconds)?Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0'):'—';}
function signed(value){return Number.isFinite(value)?(value>0?'+':'')+value:'—';}
function mapLabel(match){return match.map_profile==='lod'?'DotA LoD':match.map_profile==='newyear'?'DotA NewYear':'DotA Classic';}
function profileCard(title){const card=node('section',null,'profile-card');card.append(node('h2',title));return card;}
function profileValues(entries){const dl=node('dl',null,'profile-values');for(const[label,value]of entries)dl.append(node('dt',label),node('dd',value));return dl;}
function detailLink(match,player){const a=node('a',matchDate(match.date));a.href=url({match:match.id,player:player||null});return a;}
function matchOutcome(match,person){if(!person||![1,2].includes(person.team))return node('span','Нет данных','profile-subtitle');const won=person.team===match.winner;return node('span',won?'Победа':'Поражение',won?'result-win':'result-loss');}
function profileContent(panel,p){
 const data=rankings.pools?.[pool]||{},matches=recentMatches(data,p.name);
 const heading=node('div',null,'profile-heading');const portrait=node('div',null,'profile-hero');portrait.append(heroPortrait(p));
 const identity=node('div');identity.append(node('h1',p.name),node('p',LADDER_LABELS[pool],'profile-subtitle'));
 if(p.hero_name)identity.append(node('p','Последний герой: '+p.hero_name,'profile-subtitle'));
 heading.append(portrait,identity);panel.append(heading);
 const summary=node('div',null,'profile-summary');
 const rating=profileCard('Рейтинг');const bar=node('div',null,'level-bar profile-progress');const fill=node('div',null,'level-fill');fill.style.width=Math.max(0,Math.min(100,p.progress||0))+'%';bar.append(fill,node('span','Уровень '+(p.level??1),'level-value'));rating.append(bar);
 rating.append(profileValues([['Место',format(p.rank)],['MMR',format(p.mmr)],['Опыт',format(p.xp)],['Прогресс уровня',(p.progress??0)+'%'],['Игры',format(p.rated_games)],['Победы',format(p.wins)],['Поражения',format(p.losses)]]));
 const total=p.all_result_games??0,overall=profileCard('Общая статистика');
 overall.append(profileValues([['Завершённые игры',format(total)],['Победы',format(p.all_wins)],['Поражения',format(p.all_losses)],['Процент побед',total?(100*(p.all_wins??0)/total).toFixed(1)+'%':'—'],['Убийства / смерти / помощь',[p.all_kills,p.all_deaths,p.all_assists].map(format).join(' / ')],['Крипы',format(p.all_creepkills)],['Башни',format(p.all_towerkills)]]));
 const last=profileCard('Последняя игра');if(matches.length){const m=matches[0],person=m.players.find(r=>r.name.toLowerCase()===p.name.toLowerCase());last.append(detailLink(m,p.name),node('p',mapLabel(m)),matchOutcome(m,person),node('p',matchDuration(m.duration_seconds)),node('p',m.rated?'Рейтинговая игра':'Без изменения рейтинга','profile-subtitle'));}else last.append(node('p','Пока нет записанных результатов.'));
 summary.append(rating,overall,last);panel.append(summary);
 const history=node('section',null,'match-history');history.append(node('h2','Последние игры'));
 if(!matches.length)history.append(node('p','Пока нет записей завершённых игр.','profile-subtitle'));
 else{
  const scroll=node('div',null,'table-scroll');const table=node('table',null,'history-table');table.setAttribute('aria-label','Последние игры '+p.name);
  const head=node('tr');for(const label of ['Дата','Карта','Герой','Результат','У / С / П','Время','MMR'])head.append(node('th',label));const thead=node('thead');thead.append(head);table.append(thead);const tbody=node('tbody');
  for(const m of matches){const person=m.players.find(r=>r.name.toLowerCase()===p.name.toLowerCase()),tr=node('tr');const date=node('td');date.append(detailLink(m,p.name));const hero=node('td');hero.append(heroPortrait(person));const outcome=node('td');outcome.append(matchOutcome(m,person));if(!m.rated)outcome.append(node('small','Без рейтинга','unrated-note'));tr.append(date,node('td',mapLabel(m)),hero,outcome,node('td',[person.kills,person.deaths,person.assists].map(format).join(' / ')),node('td',matchDuration(m.duration_seconds)),node('td',signed(person.mmr_delta),person.mmr_delta>0?'result-win':person.mmr_delta<0?'result-loss':''));tbody.append(tr);}
  table.append(tbody);scroll.append(table);history.append(scroll);
 }
 panel.append(history);const back=node('a','← К рейтингу');back.href=url();panel.append(back);
}
function showMatch(id,player){
 document.querySelector('.table-scroll').hidden=true;document.querySelector('.pager').hidden=true;$('table-state').hidden=true;
 const panel=$('profile');panel.hidden=false;panel.replaceChildren();const match=findMatch(rankings.pools?.[pool],id);
 if(!match){panel.append(node('h1','Матч не найден'),node('p','Этот матч отсутствует в доступной истории.'));const back=node('a','← К рейтингу');back.href=url();panel.append(back);return;}
 document.title=mapLabel(match)+' · '+matchDate(match.date)+' — Warcraft III Online';
 panel.append(node('h1',mapLabel(match)),node('p',matchDate(match.date)+' · '+matchDuration(match.duration_seconds)+' · На старте: '+match.team_sizes.join(' × '),'match-meta'));
 if(match.name)panel.append(node('p',match.name,'profile-subtitle'));
 panel.append(node('p',match.rated?'Рейтинговая игра':'Без изменения рейтинга','profile-subtitle'));
 for(const team of [1,2,...(match.players.some(p=>p.team==null)?[null]:[])]){
  const section=node('section',null,'match-team');section.append(node('h2',team==null?'Без итоговых данных':(team===1?'Свет':'Тьма')+' — '+(match.winner===team?'Победа':'Поражение'),team==null?'profile-subtitle':match.winner===team?'result-win':'result-loss'));
  const scroll=node('div',null,'table-scroll'),table=node('table',null,'history-table match-table');table.setAttribute('aria-label',team==null?'Игроки без итоговых данных':team===1?'Команда Света':'Команда Тьмы');const head=node('tr');for(const label of ['Герой','Игрок','У','С','П','Крипы','Добивания','Лес','Башни','Бараки','Курьеры','MMR','XP'])head.append(node('th',label));const thead=node('thead');thead.append(head);const body=node('tbody');
  for(const p of match.players.filter(p=>p.team===team)){const row=node('tr');const hero=node('td');hero.append(heroPortrait(p));const name=node('td');name.append(linkPlayer(p));row.append(hero,name);for(const key of ['kills','deaths','assists','creepkills','creepdenies','neutralkills','towerkills','raxkills','courierkills'])row.append(node('td',format(p[key])));row.append(node('td',signed(p.mmr_delta)),node('td',Number.isFinite(p.xp_gained)?'+'+p.xp_gained:'—'));body.append(row);}
  table.append(thead,body);scroll.append(table);section.append(scroll);panel.append(section);
 }
 if(match.mode_source){
  const lane={'only-mid':'Только мид','no-mid':'Без мида','no-top':'Без верхней линии','no-bottom':'Без нижней линии','all-lanes':'Все линии'}[match.lane_mode];
  const source=match.mode_source==='map-event'?'событие карты в реплее':'команда в журнале матча';
  if(lane)panel.append(node('p',lane+' · '+source,'profile-subtitle'));
 }
 const back=node('a',player?'← К профилю '+player:'← К рейтингу');back.href=url({player:player||null});panel.append(back);
}

const $=id=>document.getElementById(id);
const params=new URLSearchParams(location.search);
const pool=poolForLocation(location.pathname,location.search);
if(location.pathname!==LADDER_PATHS[pool])location.replace(ladderUrl(pool,Object.fromEntries(params))+location.hash);
const mode='live';
let term=params.get('q')??'',sort=params.get('sort')??'rank',dir=params.get('dir')??'asc',page=Number(params.get('page'))||1;
const archived={players:[]};
let rankings=JSON.parse($('rankings-data').textContent);
const format=value=>Number.isFinite(value)?value.toLocaleString('ru-RU'):'—';
function url(changes={}){return ladderUrl(pool,{q:term,sort,dir,page,...changes});}
function node(tag,text,className){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(className)n.className=className;return n;}
function activePlayers(){return mode==='archive'?archived.players:(rankings.pools?.[pool]?.players??[]);}
function linkPlayer(p){const a=node('a',p.name);a.href=url({player:p.name});return a;}
function heroPortrait(p){
 const name=p.hero_name||'';const key=name.normalize('NFKC').replace(/\u2019/g,"'").toLowerCase().trim().replace(/\s+/g,' ');
 const source=HERO_PORTRAITS[key];
 if(!source)return node('span','—');
 const img=node('img',null,'hero-portrait');img.src=source;img.alt=name;img.title=name;img.width=22;img.height=22;img.loading='lazy';img.decoding='async';
 img.addEventListener('error',()=>img.replaceWith(node('span','—')),{once:true});return img;
}
function row(p){
 const tr=document.createElement('tr');tr.append(node('td',p.rank??'—'));
 const level=node('td');
 if(Number.isFinite(p.level)&&Number.isFinite(p.progress)){
  const bar=node('div',null,'level-bar');const fill=node('div',null,'level-fill');fill.style.width=Math.max(0,Math.min(100,p.progress))+'%';bar.append(fill,node('span',p.level,'level-value'));bar.setAttribute('aria-label','Уровень '+p.level+', прогресс '+p.progress+'%');level.append(bar);
 }else level.textContent='—';
 tr.append(level,node('td',mode==='archive'?(p.clan||'—'):format(rankings.rating_status==='active'?p.rated_games:p.appearances)));
 const portrait=node('td');portrait.append(heroPortrait(p));tr.append(portrait);
 const name=node('td',null,'player-cell');name.append(linkPlayer(p));tr.append(name,node('td',format(p.mmr)),node('td',Number.isFinite(p.xp)?format(p.xp):'—'),node('td',format(p.wins)),node('td',format(p.losses)));return tr;
}
function showProfile(name){
 document.querySelector('.table-scroll').hidden=!!name;document.querySelector('.pager').hidden=!!name;$('table-state').hidden=!!name;
 const panel=$('profile');panel.replaceChildren();if(!name){panel.hidden=true;return;}
 panel.hidden=false;const p=playerProfile(activePlayers(),name);
 if(!p){const back=node('a','← К таблице');back.href=url({player:null});panel.append(node('h1','Игрок не найден'),node('p','В выбранном разделе нет записи об этом игроке.'),back);return;}
 document.title=p.name+' — Warcraft III Online';profileContent(panel,p);
}
function render(){
 const isArchive=mode==='archive';const label=LADDER_LABELS[pool];
 document.title=label+' — Warcraft III Online';
 $('crumb').textContent=isArchive?'Lordaeron · Solo · 2007':label;
 $('classic-link').setAttribute('aria-current',pool==='classic'?'page':'false');$('lod-link').setAttribute('aria-current',pool==='lod'?'page':'false');
 $('portrait-heading').textContent='Последний герой';
 $('clan-heading').textContent='Игры';$('clan-heading').dataset.sort=rankings.rating_status==='active'?'rated_games':'appearances';
 const selected=selectPlayers(activePlayers(),{term,sort,dir,page,size:20});page=selected.page;
 $('players').replaceChildren();for(const p of selected.rows)$('players').append(row(p));
 if(!selected.rows.length){const tr=node('tr');const td=node('td',term?'Игроки по этому запросу не найдены.':'Пока нет записей зачтённых матчей.', 'empty-cell');td.colSpan=9;tr.append(td);$('players').append(tr);}
 $('table-state').textContent=(isArchive?'Исторические данные · ':'')+selected.total+' игроков · страница '+page+' из '+selected.pages;
 $('page-list').replaceChildren();for(let i=1;i<=selected.pages;i++){if(i===page)$('page-list').append(node('span',i));else{const b=node('button',i);b.type='button';b.addEventListener('click',()=>{page=i;render();});$('page-list').append(b);}}
 $('first-page').disabled=$('previous-page').disabled=page<=1;$('next-page').disabled=$('last-page').disabled=page>=selected.pages;
 $('first-page').onclick=()=>{page=1;render();};$('previous-page').onclick=()=>{page--;render();};$('next-page').onclick=()=>{page++;render();};$('last-page').onclick=()=>{page=selected.pages;render();};
 for(const b of document.querySelectorAll('[data-sort]')){b.closest('th').setAttribute('aria-sort',b.dataset.sort===sort?(dir==='asc'?'ascending':'descending'):'none');}
 if(params.get('match'))showMatch(params.get('match'),params.get('player'));else showProfile(params.get('player'));
}
$('player-search').value=term;
$('search-form').addEventListener('submit',e=>{e.preventDefault();term=$('player-search').value.trim();page=1;render();});
for(const b of document.querySelectorAll('[data-sort]'))b.addEventListener('click',()=>{dir=sort===b.dataset.sort&&dir==='asc'?'desc':'asc';sort=b.dataset.sort;page=1;render();});
render();
if(location.protocol==='http:'||location.protocol==='https:')fetch('data/rankings.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();}).then(data=>{if(data.schema_version!==1||!data.pools)throw Error('Unsupported data');rankings=data;render();}).catch(()=>{const message=$('data-update-error');message.textContent='Не удалось обновить данные. Показана сохранённая копия.';message.hidden=false;});

})();
