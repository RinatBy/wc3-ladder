(()=>{
  'use strict';
  if(location.hash){location.replace('/legacy'+location.hash);return;}
  const $=id=>document.getElementById(id);
  let csrf='',job=null,request=null,working=false,polling=false;
  const messages={session_expired:'Сессия истекла. Обновите страницу.',session_limit:'Слишком много подключений. Попробуйте позже.',rate_limit:'Слишком частые запросы. Подождите и попробуйте позже.',upload_pending:'Предыдущая карта ещё проверяется.',service_busy:'Хостер занят. Попробуйте позже.',temporarily_unavailable:'Хостинг временно недоступен. Попробуйте позже.',rooms_busy:'Оба хостера заняты. Карта сохранена — попробуйте создать игру позже.',already_hosting:'У вас уже есть комната или заявка на её создание.',ip_rooms_full:'Для вашей сети уже созданы две комнаты. Дождитесь завершения одной из игр.',room_unavailable:'Такое название занято или комната ещё освобождается. Попробуйте другое название чуть позже.',confirmation_timeout:'Хостер не подтвердил создание. Обновите страницу через минуту перед повторной попыткой.',controller_unavailable:'Бот временно недоступен. Попробуйте позже.',map_not_ready:'Дождитесь проверки карты.',invalid_size:'Выберите карту до 32 МБ.',not_found:'Заявка не найдена в этой сессии.',invalid_request:'Не удалось отправить запрос.',invalid_csrf:'Обновите страницу и повторите попытку.',wrong_origin:'Откройте страницу по адресу maps.wc3.uplay2.ru.'};
  Object.assign(messages,{'This is not a Warcraft map archive.':'Файл не является картой Warcraft. Изменение расширения не меняет его содержимое.','Choose a .w3x or .w3m file, up to 32 MiB.':'Выберите карту .w3x или .w3m до 32 МБ.','Incomplete upload. Request a new link and retry.':'Загрузка прервалась. Подождите минуту и отправьте карту ещё раз.','Map storage is full. Contact the administrator.':'Хранилище карт заполнено. Обратитесь к администратору.'});
  function message(error){return messages[error]||((error||'').startsWith('Room name:')?'Название: до 30 знаков, латинские буквы, цифры и пробелы.':error||'Ошибка соединения. Повторите попытку.');}
  function text(id,value,error=false){$(id).textContent=value;$(id).className=error?'error':'';}
  async function api(path,options={}){
    let response;
    try{response=await fetch(path,{credentials:'same-origin',cache:'no-store',...options,headers:{...(options.method==='POST'?{'X-CSRF-Token':csrf}:{}),...(options.headers||{})}});}catch{throw Error('Соединение прервалось. Обновите страницу, чтобы проверить состояние заявки.');}
    let data;try{data=await response.json();}catch{throw Error('Сервис временно недоступен. Обновите страницу и повторите попытку.');}
    if(!response.ok)throw Error(message(data.error));return data;
  }
  function buttons(){
    $('upload').disabled=!csrf||working||!!(job&&['receiving','pending'].includes(job.state))||!$('file').files.length;
    $('create').disabled=!csrf||working||!job||job.state!=='ready'||!!(request&&['queued','dispatched','advertised'].includes(request.state));
  }
  function render(){
    $('hosting').hidden=!job||job.state!=='ready';
    if(job){
      if(job.state==='ready'){text('upload-status','Карта проверена и готова к хостингу.');$('map-name').textContent=job.title;}
      else if(job.state==='rejected')text('upload-status','Файл не прошёл проверку карты. Выберите другую карту.',true);
      else text('upload-status','Карта получена. Проверяем совместимость…');
    }
    if(request){
      $('room').value=request.room;
      if(request.state==='advertised'){text('room-status','Комната «'+request.room+'» создана. Откройте пользовательские игры в Warcraft и найдите её.');$('room-status').className='success';}
      else if(request.state==='failed')text('room-status',message(request.error),true);
      else if(request.state==='ended')text('room-status','Комната завершена. Можно создать следующую.');
      else text('room-status','Создаём комнату «'+request.room+'»…');
    }
    buttons();
  }
  async function poll(){
    if(polling)return;polling=true;
    try{
      while((job&&['receiving','pending'].includes(job.state))||(request&&['queued','dispatched','advertised'].includes(request.state))){
        await new Promise(resolve=>setTimeout(resolve,2000));
        const state=await api('/api/state');job=state.job;request=state.request;render();
      }
    }catch(error){text('page-status',error.message,true);}finally{polling=false;}
  }
  $('file').addEventListener('change',buttons);
  $('upload').onclick=async()=>{
    const file=$('file').files[0];if(!file||working)return;
    if(!/\.w3[xm]$/i.test(file.name)||file.size>32*1024*1024||file.size<4){text('upload-status','Выберите файл .w3x или .w3m до 32 МБ.',true);return;}
    working=true;buttons();text('upload-status','Загружаем карту…');
    try{
      const data=await api('/api/upload',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Map-Name':encodeURIComponent(file.name)},body:file});
      job={id:data.id,state:'pending',title:file.name};request=null;render();poll();
    }catch(error){text('upload-status',error.message,true);}finally{working=false;buttons();}
  };
  $('create').onclick=async()=>{
    if(working||!job||job.state!=='ready')return;
    const room=$('room').value.trim();if(!/^[A-Za-z0-9][A-Za-z0-9 _.,!()\[\]+-]{0,29}$/.test(room)){text('room-status','Название: до 30 знаков, латинские буквы, цифры и пробелы.',true);return;}
    working=true;buttons();
    try{
      const key='hostmap-request-'+job.id;
      let identifier=sessionStorage.getItem(key);
      if(!identifier||request&&['failed','ended'].includes(request.state)){identifier=crypto.randomUUID().replaceAll('-','');sessionStorage.setItem(key,identifier);}
      request=await api('/api/host',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:identifier,job:job.id,room})});render();poll();
    }catch(error){text('room-status',error.message,true);}finally{working=false;buttons();}
  };
  api('/api/session',{method:'POST',body:''}).then(state=>{csrf=state.csrf;job=state.job;request=state.request;text('page-status','');render();poll();}).catch(error=>text('page-status',error.message,true));
})();
