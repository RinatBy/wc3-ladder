"""Reuse the rating site's actual shell and assets, without touching live ranking data."""
from pathlib import Path
import re
import shutil
from ui_assets import WEB_FILES

ROOT=Path(__file__).resolve().parent
SITE=ROOT.parent/'sites/warcraft-ladder-2007'
TAG='20261110-menu5'
NAV='''  <nav class="site-navigation" aria-label="Разделы сайта">
    <a href="https://wc3.uplay2.ru/" id="main-link">Главная</a>
    <div class="rating-menu">
      <button class="rating-toggle" type="button">Рейтинг <span class="down-arrow" aria-hidden="true"></span></button>
      <div class="rating-options">
        <a href="https://wc3.uplay2.ru/classic/" id="classic-link">DotA Classic</a>
        <a href="https://wc3.uplay2.ru/lod/" id="lod-link">DotA LoD</a>
      </div>
    </div>
    <a href="https://maps.wc3.uplay2.ru/" id="hosting-link">Захостить карту</a>
  </nav>'''
HEADER='''  <header class="site-header gateway-header">
    <div class="original-header">__NAV__</div>
  </header>'''


def footer(form='',host=False):
    image='/web/arrow-left.gif' if host else 'assets/war3/images/ladder-revise/arrow-left.gif'
    return f'''  <footer class="site-footer">
    <a href="https://wc3.uplay2.ru/" class="return-link"><img src="{image}" alt="">На главную</a>
    <span class="footer-name">Warcraft III Online</span>
    {form}
  </footer>'''


def patch_site(text,home=False):
    form=re.search(r'<form id="search-form".*?</form>',text,re.S)
    text=re.sub(r'\s*<nav class="(?:hosting-navigation|site-navigation)".*?</nav>','',text,flags=re.S)
    replacement=HEADER.replace('__NAV__',NAV)
    if home: replacement=replacement.replace('id="main-link"','id="main-link" aria-current="page"')
    text,count=re.subn(r'<header class="site-header[^\"]*">.*?</header>',replacement,text,count=1,flags=re.S)
    if count!=1: raise ValueError('Expected one site header')
    text=re.sub(r'<nav class="crumbs".*?</nav>','<span id="crumb" class="sr-only">Рейтинг</span>',text,count=1,flags=re.S)
    text,count=re.subn(r'<footer class="site-footer[^\"]*">.*?</footer>',lambda _:footer(form[0] if form else ''),text,count=1,flags=re.S)
    if count!=1: raise ValueError('Expected one site footer')
    return re.sub(r'ladder\.css\?v=[^"\s]+','ladder.css?v='+TAG,text)


def main():
    css=SITE/'ladder.css'
    base=css.read_text(encoding='utf-8').split('/* Shared original site chrome,')[0].rstrip()
    shared=(SITE/'site-shell.css').read_text(encoding='utf-8')
    css.write_text(base+'\n\n'+shared,encoding='utf-8')
    for name in ('home.html','page.html'):
        path=SITE/name
        path.write_text(patch_site(path.read_text(encoding='utf-8'),home=name=='home.html'),encoding='utf-8')
    web=ROOT/'web'
    text=(web/'index.html').read_text(encoding='utf-8')
    text=re.sub(r'<body.*?<main[^>]*>',lambda _:'<body class="hosting-page">\n'+HEADER.replace('__NAV__',NAV.replace('id="hosting-link"','id="hosting-link" aria-current="page"'))+'\n<main class="hosting-main">',text,count=1,flags=re.S)
    text=text.replace('<main class="hosting-main"><div class="frame">','<main class="hosting-main"><section class="ranking-frame"><div class="frame-top"><i></i><i></i></div><div class="frame-middle"><div class="hosting-content">')
    text=re.sub(r'</div></main><footer>.*?</footer>',lambda _:'</div></div><div class="frame-bottom"><i></i><i></i></div></section></main>\n'+footer(host=True),text,count=1,flags=re.S)
    text=re.sub(r'<footer class="site-footer">.*?</footer>',lambda _:footer(host=True),text,count=1,flags=re.S)
    text=re.sub(r'/web/style\.css(?:\?v=[^"\s]+)?', '/web/style.css?v='+TAG, text)
    (web/'index.html').write_text(text,encoding='utf-8')
    hosting='''
.hosting-content{max-width:760px;margin:auto;padding:24px 32px;background:#000;color:#e2d6bd;font:13px/1.6 Arial,Helvetica,sans-serif}
.hosting-content h1{font:normal 26px Georgia,serif;color:#e4c66b;margin:0 0 12px}.hosting-content .intro{color:#c2b69e;margin-bottom:24px}
.hosting-content section{border-top:1px solid #4c4030;padding:20px 0}.hosting-content h2{font:normal 19px Georgia,serif;color:#e5c66c;margin:0 0 20px}
.hosting-content h2 span{display:inline-grid;place-items:center;width:26px;height:26px;border:2px ridge #777;margin-right:10px;background:#21190f;color:#e5c66c;font:inherit}
.hosting-content label{display:block;margin:12px 0 9px}.hosting-content input{font:14px Arial;background:#080808;color:#fff;border:1px solid #716454;padding:10px;max-width:100%}
.hosting-content input[type=file]{display:block;width:100%;cursor:pointer}.hosting-content input[type=file]::file-selector-button{background:#222;color:#e5c66c;border:1px solid #777;padding:8px 12px;margin-right:12px;cursor:pointer}
.hosting-content input[type=text]{width:320px}.hosting-content button{font:bold 15px Georgia,serif;color:#ffd100;background:linear-gradient(#14175c,#030425);border:4px ridge #625d51;padding:11px 23px;cursor:pointer;margin-top:8px}
.hosting-content button:disabled{opacity:.45;cursor:default}.hosting-content button:hover:enabled{filter:brightness(1.3)}.hosting-content .muted{color:#a99c82;font-size:12px;line-height:1.6}
.hosting-content .notice{padding:13px 0;border-top:1px solid #4c4030}.hosting-content .map-name{color:#fff;overflow-wrap:anywhere}#upload-status,#room-status{overflow-wrap:anywhere}
.hosting-content .success{color:#a7d288}.hosting-content .error{color:#e9aa96}.hosting-content code{color:#fff}@media(max-width:560px){.hosting-content{padding:18px 12px}.hosting-content h1{font-size:24px}.hosting-content button{width:100%}}
'''
    host_css=base+'\n\n'+shared+'\n'+hosting
    host_css=re.sub(r'assets/war3/images/ladder-revise/([^\)\'\"]+)',lambda m:'/web/'+('header.gif' if m[1] in ('gatewayselect-header-w3xp.gif','headers/W3XP-Lordaeron-Ladders.gif') else m[1]),host_css)
    (web/'style.css').write_text(host_css,encoding='utf-8')
    assets=SITE/'dist/assets/war3/images/ladder-revise'
    shutil.copyfile(assets/'headers/W3XP-Lordaeron-Ladders.gif',web/'header.gif')
    for name in WEB_FILES:
        if name.endswith('.gif') and name not in ('header.gif','wood.gif'): shutil.copyfile(assets/name,web/name)
    print('Built shared header, four-link navigation, original frames and aligned footer')


if __name__=='__main__': main()
