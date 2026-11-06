"""Approved, deterministic team rating and account progression, policy version 1."""
from collections import Counter
import math

METRICS=('kills','deaths','assists','creepkills','creepdenies','neutralkills','towerkills','raxkills','courierkills')


def level_progress(xp):
    level=1+math.isqrt(max(0,int(xp))//100)
    low=100*(level-1)**2
    return level, round(100*(xp-low)/(100*level**2-low),2)


def mmr_delta(own,opponent,won):
    expectation=1/(1+10**max(-12,min(12,(opponent-own)/400)))
    magnitude=max(1,min(49,math.floor(50*((1-expectation) if won else expectation)+0.5)))
    return magnitude if won else -magnitude


def experience(won,kills,assists,team_kills,team_towers,team_barracks):
    participation=max(0,min(1,(kills+assists)/max(1,team_kills)))
    bonus=math.floor(40*participation+0.5)+max(0,min(10,2*team_towers+5*team_barracks))
    return 50+50*int(won)+bonus


def eligible(event):
    people=event['players']
    return (event.get('roster_valid',True) and event['winner'] in (1,2) and len(people)==10
            and len({p['name'].casefold() for p in people})==10
            and Counter(p['team'] for p in people)=={1:5,2:5}
            and Counter(p['start_team'] for p in people)=={1:5,2:5})


def replay(events):
    players={};seen=set();count=0;accepted=[]
    for event in sorted(events,key=lambda e:(e['date'],e['id'])):
        if event['id'] in seen: continue
        seen.add(event['id'])
        if not eligible(event): continue
        people=event['players'];teams={t:[p for p in people if p['team']==t] for t in (1,2)}
        for p in people:
            key=p['name'].casefold()
            if key not in players:
                players[key]=dict(mmr=1000,xp=0,wins=0,losses=0,rated_games=0,**{m:0 for m in METRICS})
        averages={t:sum(players[p['name'].casefold()]['mmr'] for p in team)/5 for t,team in teams.items()}
        delta=mmr_delta(averages[1],averages[2],event['winner']==1)
        for t,team in teams.items():
            totals={m:sum(p.get(m,0) or 0 for p in team) for m in ('kills','towerkills','raxkills')}
            for p in team:
                state=players[p['name'].casefold()];won=t==event['winner']
                state['mmr']=max(0,state['mmr']+(delta if t==1 else -delta))
                state['xp']+=experience(won,p.get('kills',0) or 0,p.get('assists',0) or 0,totals['kills'],totals['towerkills'],totals['raxkills'])
                state['wins']+=int(won);state['losses']+=int(not won);state['rated_games']+=1
                for metric in METRICS: state[metric]+=p.get(metric,0) or 0
        count+=1;accepted.append(event['id'])
    for state in players.values(): state['level'],state['progress']=level_progress(state['xp'])
    return dict(players=players,rated_matches=count,match_ids=accepted)
