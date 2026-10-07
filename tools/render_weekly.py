"""주간운세 페이지 생성기.

사용법:  python3 tools/render_weekly.py 2026-10-04
  data/week-YYYY-MM-DD.json (계산 결과)와 texts/week-YYYY-MM-DD.json (현암 선생 풀이 문장)을 합쳐
  weekly/YYYY-MM-DD.html 을 만들고, weekly/index.html (모음 목록)을 다시 만든다.
  texts 파일이 없거나 항목이 비어 있으면 계산 결과로 만든 기본 문장을 쓴다.
"""
import sys, os, json, re, html, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E = html.escape

POSN = {'년':'원국 윗자리','월':'일터·사회 자리','일':'배우자·집 자리','시':'아랫사람·결과 자리','대운':'10년 흐름','세운':'올해 글자','월운':'이달 글자'}
SPOSN = {'일간':'나 자신','월간':'원국 월간','년간':'원국 년간','시간':'원국 시간','대운간':'대운 윗글자','세운간':'올해 윗글자','월운간':'이달 윗글자'}
ACTN = {'충':'정면 충돌','합':'손잡음','형':'꺾고 다듬음','파':'깨뜨림','해':'은근한 방해','원진':'괜히 불편함','귀문':'예민함','자형':'스스로 볶음','복음':'같은 글자 겹침'}
PRIO = {'삼형':9,'충':8,'합':6,'형':5,'원진':4,'해':4,'귀문':3,'파':3,'자형':3,'복음':2}
POSW = {'일':3,'월':2.5,'년':1.5,'시':1.5,'대운':1.2,'세운':1,'월운':1}
ELK = {'水':'물','木':'나무','火':'불','土':'흙','金':'쇠'}
CATK = {'비견':'비겁','겁재':'비겁','식신':'식상','상관':'식상','편재':'재성','정재':'재성','편관':'관성','정관':'관성','편인':'인성','정인':'인성'}
TEN_E = {'비견':'나와 같은 기운','겁재':'경쟁하는 기운','식신':'꾸준히 만들어 내는 힘','상관':'틀을 깨는 표현','편재':'크게 움직이는 돈','정재':'차곡차곡 쌓는 돈','편관':'나를 누르는 압박','정관':'규칙과 질서','편인':'독특한 생각·직감','정인':'나를 돕고 보살피는 기운'}

def band(v):
    return '흐름이 좋아요' if v >= 70 else '무난한 편 이상이에요' if v >= 60 else '보통이에요' if v >= 50 else '조심이 필요해요' if v >= 40 else '부담이 큰 편이에요'
def col(v):
    return 'var(--g5)' if v >= 70 else 'var(--g4)' if v >= 60 else 'var(--g3)' if v >= 50 else 'var(--g2)' if v >= 40 else 'var(--g1)' if v >= 30 else 'var(--g0)'

def josa(w, a='와', b='과'):
    c = w.rstrip(')').rstrip()[-1]
    if not ('가' <= c <= '힣'): return w + a
    return w + (b if (ord(c) - 0xAC00) % 28 else a)

def act_text(a, pos):
    if a == '삼형': return '호랑이·뱀·원숭이가 서로 꺾는 관계(인사신 삼형)' if pos == '인사신' else '소·개·양이 서로 꺾는 관계(축술미 삼형)'
    return f"{josa(POSN[pos])} {ACTN[a]}({a})"

def factors(d):
    fs = []
    for a, pos in d['acts']:
        w = PRIO.get(a, 2) * (POSW.get(pos, 2) if a != '삼형' else 3)
        fs.append((w, a, pos))
    fs.sort(key=lambda x: -x[0])
    return fs

PAT = {
 ('충','일'): '집 안의 일정이나 말이 엇갈리기 쉬워요. 가까운 사람과 결론 내는 대화가 꼬이기 쉬운 모양이에요.',
 ('충','월'): '맡은 일의 방향이나 위치가 흔들리는 일이 생기기 쉬워요. 계획이 바뀌거나 지시가 뒤집히는 식이에요.',
 ('충','년'): '윗사람·부모님 쪽과 생각이 어긋나는 일이 생기기 쉬워요.',
 ('충','시'): '아랫사람·자녀·결과물 쪽 일정이 바뀌기 쉬워요. 오후 이후 약속이 틀어지는 식이에요.',
 ('충','대운'): '요즘 10년 흐름의 큰 계획(돈·자리)을 다시 따져 보게 되는 일이 생기기 쉬워요.',
 ('충','세운'): '올해 내내 쌓인 압박이 한 번 터지거나 풀리는 계기가 생기기 쉬워요.',
 ('충','월운'): '이달의 분위기와 반대 방향의 일이 끼어들어 흐름이 끊기기 쉬워요.',
 ('합','일'): '가족·배우자와 손발이 잘 맞아 집안일을 함께 정하기 좋아요.',
 ('합','월'): '일터에서 협업과 거래가 잘 맺어지는 모양이에요.',
 ('합','년'): '윗사람·오래된 인연의 도움이나 조언이 들어오기 쉬워요.',
 ('합','시'): '후배·자녀·결과물 쪽 일이 매끄럽게 엮여요.',
 ('합','대운'): '10년 흐름과 손을 잡아 현실 계획이 하나로 모여요.',
 ('합','세운'): '올해의 흐름과 손을 잡아 묵은 일이 정리되기 쉬워요.',
 ('합','월운'): '이달 흐름에 잘 올라타는 날이에요.',
 ('형','월'): '일터에서 조정·수정 요청이 생기기 쉬워요.',
 ('형','일'): '가까운 사이에서 말이 날카로워지기 쉬워요.',
 ('해','일'): '가까운 사람에게 괜히 서운한 마음이 생기기 쉬워요.',
 ('원진','일'): '집에서 사소한 말에 신경이 곤두서기 쉬워요.',
 ('귀문','일'): '생각이 많아지고 잠이 얕아지기 쉬워요.',
 ('자형','일'): '혼자 같은 생각을 곱씹기 쉬워요.',
}
def pattern_for(a, pos):
    if a == '삼형': return '일정·서류·약속이 한꺼번에 얽히기 쉬워요. 하나가 틀어지면 다른 것도 따라 흔들리는 모양이에요.'
    if (a, pos) in PAT: return PAT[(a, pos)]
    if a in ('원진','귀문'): return f"{POSN[pos]} 쪽 일로 괜히 예민해지기 쉬워요."
    if a in ('해','파'): return f"{POSN[pos]} 쪽 일이 작게 어긋나기 쉬워요."
    if a in ('자형','복음'): return f"{josa(POSN[pos])} 같은 기운이 겹쳐 같은 문제를 다시 붙잡기 쉬워요."
    return f"{POSN[pos]} 쪽에서 변화가 생기기 쉬워요."

TG_PAT = {
 '관성': '위에서 요청이나 평가가 들어오고, 책임이 내 쪽으로 기울기 쉬워요.',
 '인성': '서류·검토·생각할 거리가 늘고, 결정보다 준비에 시간이 쓰이기 쉬워요.',
 '식상': '말과 아이디어가 많아지고, 손이 빨라져 실무가 진척되기 쉬워요.',
 '재성': '돈·조건·숫자 이야기가 많아지고, 현실적인 판단을 하게 되기 쉬워요.',
 '비겁': '동료·친구와 엮이는 일이 늘고, 비교와 경쟁 심리가 올라오기 쉬워요.',
}
DO = {'관성':'맡은 일의 범위를 글로 확인하기','인성':'서류·자료를 꼼꼼히 검토하기','식상':'아이디어를 메모하고 실무를 몰아서 처리하기','재성':'수입·지출을 숫자로 정리하기','비겁':'믿을 만한 동료와 역할 나누기'}
AVOID = {'관성':'즉석에서 추가 책임 떠안기','인성':'생각만 하다 결정 미루기를 반복하기','식상':'윗사람 앞에서 직설 던지기','재성':'확인 안 한 거래나 조건에 바로 답하기','비겁':'경쟁심에 끌린 지출'}
DO_A = {('충','일'):'집안 일정은 미리 공유하기',('충','월'):'변경 가능성을 열어 두고 대안 준비하기',('합','일'):'가족과 함께 정할 일을 오늘 정하기',('합','월'):'협업 제안이나 거래 마무리하기',('합','년'):'윗사람·선배에게 조언 구하기',('삼형','*'):'일정을 하나씩 줄이고 확인 또 확인하기'}
AV_A = {('충','일'):'집에서 결론 내는 대화',('충','월'):'업무 방향을 혼자 확정하기',('충','시'):'오후 일정 빽빽하게 잡기',('충','년'):'윗사람 앞 즉석 반박',('삼형','*'):'계약·서명과 무리한 운전',('원진','일'):'예민한 주제 꺼내기',('해','일'):'서운함을 말없이 쌓아 두기'}

def domain_lines(p, d):
    sc = d['scores']; cs, cb = CATK[d['ts']], CATK[d['tb']]
    fs = factors(d); top = fs[0] if fs else None
    def has(a, pos): return any(x[1] == a and x[2] == pos for x in fs)
    tg = f"오늘 윗글자는 {TEN_E[d['ts']]}({d['ts']}), 아랫글자는 {TEN_E[d['tb']]}({d['tb']})예요."
    L = {}
    w = '일터·사회 자리와 손잡는 날이라 협업이 잘 풀려요.' if has('합','월') else '일터·사회 자리가 부딪혀 역할·계획이 흔들리기 쉬워요.' if has('충','월') else TG_PAT.get(cs, '')
    L['업무'] = (sc['업무'], band(sc['업무']), w + (' 실수는 확인 한 번으로 막을 수 있어요.' if sc['업무'] < 50 else ' 보고·회의에서 내 몫을 분명히 말하기 좋아요.' if sc['업무'] >= 60 else ''))
    if '겁재' in (d['ts'], d['tb']): m = '경쟁하는 기운(겁재)이 있어 나가는 돈이 늘기 쉬워요. 빌려주기와 체면 지출은 줄이세요.'
    elif '재성' in (cs, cb): m = '돈의 기운(재성)이 들어와 돈 이야기·조건·계약이 오가기 쉬워요.' + (' 들어오는 흐름이 있는 쪽이에요.' if sc['재물'] >= 55 else ' 다만 확인 없이 정하면 손해가 나기 쉬워요.')
    elif '식상' in (cs, cb): m = '재주와 실무가 돈으로 이어지는 흐름이에요. 성과를 숫자로 남겨 두세요.'
    elif '관성' in (cs, cb): m = '돈보다 책임이 먼저 오는 날이에요. 큰돈 결정은 다른 날로 미루세요.'
    else: m = '큰돈의 움직임은 적은 날이에요. 예상 밖 지출만 막으면 돼요.'
    L['재물'] = (sc['재물'], band(sc['재물']), m)
    if has('합','년') or has('합','시'): r = '윗사람이나 아랫사람과 손잡는 작용이 있어 부탁이 잘 통해요.'
    elif any(x[1] in ('원진','해') for x in fs): r = '괜히 불편하거나 서운한 감정이 끼기 쉬워요. 거리를 조금 두면 편해요.'
    elif '비겁' in (cs, cb): r = '동료·친구와 엮이는 일이 많아요. 비교하는 말은 피하세요.'
    elif d['ts'] == '상관' or d['tb'] == '상관': r = '표현이 날카로워지기 쉬워요. 맞는 말일수록 부드럽게.'
    else: r = '사람 관계는 큰 굴곡 없이 흘러가요. 새로운 사람보다 기존 사람에게 집중하기 좋아요.'
    L['인간관계'] = (sc['인간관계'], band(sc['인간관계']), r)
    if has('충','일'): lv = '배우자·집 자리를 정면으로 치는 날이에요. 관계가 있다면 결론 내는 대화를 미루고, 없다면 새 만남에서 서두르지 마세요.'
    elif has('합','일'): lv = '배우자·집 자리와 손잡는 날이에요. 관계가 있다면 함께 정할 일을 정하기 좋고, 없다면 편안한 인연이 눈에 들어오기 쉬워요.'
    elif has('해','일') or has('원진','일'): lv = '배우자·집 자리와 은근히 불편한 작용이 있어요. 사소한 말에 서운해지기 쉬우니 말끝을 부드럽게 하세요.'
    else: lv = '배우자 자리에 큰 작용이 없는 날이에요. 평소처럼 지내면 돼요.'
    L['연애·부부'] = (sc['연애·부부'], band(sc['연애·부부']), lv)
    if has('충','년'): fm = '원국 윗자리와 부딪혀 부모님·어른과 생각이 엇갈리기 쉬워요.'
    elif has('합','년'): fm = '원국 윗자리와 손잡아 어른들과의 시간이 편해요.'
    elif '인성' in (cs, cb): fm = '나를 돕는 기운(인성)이 있어 가족에게서 힘을 얻기 좋아요.'
    else: fm = '가족 쪽은 무난한 흐름이에요.'
    L['가족'] = (sc['가족'], band(sc['가족']), fm)
    nch = sum(1 for x in fs if x[1] == '충')
    if sc['결정'] >= 62: dc = '확정하기 좋은 날에 가까워요.'
    elif sc['결정'] >= 48: dc = '검토하기 좋은 날이에요. 확정은 한 번 더 생각한 뒤에.'
    else: dc = '기다리는 것이 좋은 날이에요.'
    dc += f" 오늘 정면 충돌(충)이 {nch}개 있어요." if nch else ' 큰 충돌이 없는 날이에요.'
    if any(x[1] == '삼형' for x in fs): dc += ' 세 글자가 꺾는 관계가 있어 계약·서명은 피하세요.'
    L['결정'] = (sc['결정'], band(sc['결정']), dc)
    mv = '집·일터 자리의 충돌이 있어 이동 계획이 바뀌기 쉬워요. 시간 여유를 두세요.' if (has('충','일') or has('충','월')) else '이동에 큰 부담은 없어요.'
    if any(x[1] == '삼형' for x in fs): mv = '일정이 서로 얽히는 날이에요. 운전·이동은 서두르지 말고 여유 있게.'
    L['이동'] = (sc['이동'], band(sc['이동']), mv)
    if '비겁' in (cs, cb): sp = '충동구매가 생기기 쉬워요. 필요한 것만 사고, 고가 제품과 장기 계약은 미루세요.'
    elif d['ts'] == '식신' or d['tb'] == '식신': sp = '먹고 누리는 쪽 소비가 늘기 쉬워요. 필요한 소비는 괜찮아요.'
    elif '인성' in (cs, cb): sp = '지갑이 닫히는 날이에요. 필요한 소비 위주로 차분히.'
    else: sp = '필요한 소비는 괜찮고, 고가 제품은 비교 후에.'
    L['소비'] = (sc['소비'], band(sc['소비']), sp)
    ex = [e for e in d['els'] if e in [ELK[x] for x in p['excess_h']]]
    cd = (f"이미 넉넉한 {'·'.join(sorted(set(ex)))} 기운이 더해져 몸이 무겁거나 쉽게 지치는 경향이에요." if ex else f"필요한 {p['yong']} 기운이 들어와 컨디션이 가벼운 쪽이에요." if p['yong'] in d['els'] else '컨디션은 평소 수준이에요.')
    if any(x[1] == '귀문' for x in fs): cd += ' 신경이 예민해지기 쉬우니 잠을 충분히 주세요.'
    L['컨디션'] = (sc['컨디션'], band(sc['컨디션']), cd + ' 명리적 경향일 뿐, 건강 진단은 아니에요.')
    return tg, L

def todo(d):
    fs = factors(d); cs, cb = CATK[d['ts']], CATK[d['tb']]
    do, av = [], []
    for w, a, pos in fs[:4]:
        k = (a, '*') if a == '삼형' else (a, pos)
        if k in DO_A and DO_A[k] not in do: do.append(DO_A[k])
        if k in AV_A and AV_A[k] not in av: av.append(AV_A[k])
    for c in (cs, cb):
        if DO[c] not in do: do.append(DO[c])
        if AVOID[c] not in av: av.append(AVOID[c])
    fill_do = ['잠들기 전 내일 할 일 세 가지만 적기', '물 충분히 마시고 짧게 걷기', '미뤄 둔 연락 하나 하기']
    fill_av = ['늦은 밤까지 고민 붙잡기', '피곤한 상태로 큰 결정하기', '감정 섞인 메시지 보내기']
    for x in fill_do:
        if len(do) >= 3: break
        if x not in do: do.append(x)
    for x in fill_av:
        if len(av) >= 3: break
        if x not in av: av.append(x)
    return do[:3], av[:3]

def patterns(d):
    fs = factors(d); out = []
    for w, a, pos in fs:
        t = pattern_for(a, pos)
        if t not in out: out.append(t)
        if len(out) >= 2: break
    t = TG_PAT[CATK[d['ts']]]
    if t not in out: out.append(t)
    t2 = TG_PAT[CATK[d['tb']]]
    if len(out) < 3 and t2 not in out: out.append(t2)
    while len(out) < 3: out.append('큰 사건보다 평소의 흐름이 이어지는 모양이에요.')
    return out[:3]

def structure_lines(d):
    out = []
    for w, a, pos in factors(d)[:4]: out.append(act_text(a, pos))
    for el, kind in d['sams']: out.append(f"{ELK[el]}의 묶음 {'완성(삼합)' if kind=='완성' else '반쯤(반합)'}")
    for k, pos, v in d['st']:
        out.append(f"오늘 윗글자와 {SPOSN[pos]}({v}) {'손잡음(합)' if k=='합' else '정면 충돌(충)'}")
    return out or ['큰 합·충 없이 조용한 날']

def default_h(d):
    fs = factors(d)
    if fs: return f"{act_text(fs[0][1], fs[0][2])}이 중심이 되는 날이에요."
    return f"{TEN_E[d['ts']]}({d['ts']})과 {TEN_E[d['tb']]}({d['tb']})이 함께 오는 날이에요."

def week_questions(pp):
    days = pp['days']; ws = pp['week_scores']
    cnt = {}
    for d in days:
        for e in d['els']: cnt[e] = cnt.get(e, 0) + 1
    dom = max(cnt, key=cnt.get)
    yong = sum(1 for d in days if pp['yong'] in d['els']); gi = sum(1 for d in days if any(g in d['els'] for g in pp['gi']))
    acts = {}
    for d in days:
        for w, a, pos in factors(d)[:2]:
            k = act_text(a, pos); acts[k] = acts.get(k, 0) + w
    core = sorted(acts, key=lambda k: -acts[k])[:2]
    best = max(days, key=lambda d: d['scores']['기회']); worst = min(days, key=lambda d: d['scores']['종합'])
    q = [
     ('이번 주를 지배하는 오행', f"{dom} ({cnt[dom]}번, 일진 7일의 윗·아랫글자 기준)"),
     ('원국 입장에서', '도움 쪽' if dom in (pp['yong'], pp['hee']) else '부담 쪽' if dom in pp['gi'] else '중립에 가까움'),
     ('용신이 살아나는 날', f"{yong}일 ({pp['yong']})"),
     ('기신이 강해지는 날', f"{gi}일 ({'·'.join(pp['gi'])})"),
     ('핵심 작용', ' / '.join(core) if core else '큰 합·충 없음'),
     ('가장 큰 기회', f"{best['wd']}요일 ({best['gzk']}일, 기회 {best['scores']['기회']}점)"),
     ('가장 큰 위험', f"{worst['wd']}요일 ({worst['gzk']}일, 종합 {worst['scores']['종합']}점)"),
     ('사람 문제 vs 일 문제', '사람 문제가 더 커요' if ws['인간관계'] < ws['업무'] else '일 문제가 더 커요'),
     ('움직임 vs 지킴', '움직이는 쪽이 나아요' if ws['이동'] >= 55 and ws['결정'] >= 55 else '지키는 쪽이 나아요'),
     ('결정 vs 관찰', '결정하기 좋은 주' if ws['결정'] >= 58 else '관찰하는 주'),
    ]
    return q

def render(sun):
    data = json.load(open(os.path.join(ROOT, 'data', f'week-{sun}.json')))
    tp = os.path.join(ROOT, 'texts', f'week-{sun}.json')
    T = json.load(open(tp)) if os.path.exists(tp) else {}
    s0 = dt.date.fromisoformat(data['week_start']); s6 = dt.date.fromisoformat(data['week_end'])
    rng = f"{s0.year}.{s0.month:02d}.{s0.day:02d} 일요일 ~ {s6.year}.{s6.month:02d}.{s6.day:02d} 토요일"
    from weekly_engine import PEOPLE
    PX = {p['key']: p for p in PEOPLE}
    panes = []; tabs = []
    for i, pp in enumerate(data['people']):
        key = pp['key']; t = T.get(key, {}); dtexts = t.get('days', {})
        pe = PX[key]; pp['excess_h'] = pe['excess']
        ws = pp['week_scores']
        tabs.append(f'<button role="tab" data-key="{key}" aria-selected="{"true" if i==0 else "false"}"><b>{pp["name"]}</b><small>{"·".join(pp["pillars"][2:3])}일주</small></button>')
        H = []
        H.append(f'<header class="wk-head"><div class="eyebrow">현암 선생 주간운세 · {pp["name"]}</div><h1>{E(rng)}</h1>'
                 f'<div class="who">{E(pp["birth"])} · 원국 {" ".join(pp["pillars"])} (년 월 일 시)</div></header>')
        s3 = t.get('summary3') or [f"이번 주 종합 {ws['종합']}점이에요.", f"가장 좋은 날은 {pp['days'][[d['date'] for d in pp['days']].index(pp['best'][0])]['wd']}요일이에요.", f"가장 조심할 날은 {pp['days'][[d['date'] for d in pp['days']].index(pp['worst'][0])]['wd']}요일이에요."]
        H.append('<section class="wk"><h2><span class="no">0</span>이번 주 3줄 요약</h2><ol class="sum3">' + ''.join(f'<li>{E(x)}</li>' for x in s3) + '</ol></section>')
        d0 = pp['days'][0]; sw = [d for d in pp['days'] if d['switch']]
        swtxt = ''.join(f"<p class='note'>{d['wd']}요일 {d['switch'][1]} 무렵 {d['switch'][0]} 절기가 들어, 그때부터 월운이 바뀌어요.</p>" for d in sw)
        months = []
        for d in pp['days']:
            if d['month'] not in months: months.append(d['month'])
        H.append(f'<section class="wk"><h2><span class="no">1</span>분석에 사용한 사주 기준</h2><div class="tbl"><table><tbody>'
                 f'<tr><th>원국</th><td>{" · ".join(pp["pillars"])}</td></tr><tr><th>용신 · 희신</th><td>{pp["yong"]} · {pp["hee"]}</td></tr>'
                 f'<tr><th>기신</th><td>{"·".join(pp["gi"])}</td></tr><tr><th>대운</th><td>{d0["dw"]} 대운</td></tr><tr><th>세운</th><td>{d0["year"]}년</td></tr>'
                 f'<tr><th>월운</th><td>{" → ".join(m + "월" for m in months)}</td></tr></tbody></table></div>{swtxt}</section>')
        q = week_questions(pp)
        one = t.get('oneliner', '')
        H.append('<section class="wk"><h2><span class="no">2</span>이번 주 명리 구조</h2>' + (f'<p class="lead">{E(one)}</p>' if one else '') +
                 '<div class="tbl"><table><tbody>' + ''.join(f'<tr><th>{E(a)}</th><td>{E(b)}</td></tr>' for a, b in q) + '</tbody></table></div></section>')
        agg = {}
        for d in pp['days']:
            for w, a, pos in factors(d)[:3]:
                k = act_text(a, pos); agg.setdefault(k, []).append(d['wd'])
        top = sorted(agg.items(), key=lambda kv: -len(kv[1]))[:6]
        H.append('<section class="wk"><h2><span class="no">3</span>주간 핵심 합·충·형·파·해</h2><div class="chips">' +
                 ''.join(f'<span class="chip {"good" if "손잡음" in k else "bad" if ("충돌" in k or "꺾" in k) else "mid"}">{E(k)} · {"·".join(v)}</span>' for k, v in top) + '</div></section>')
        areas = [('전체운', ws['종합'])] + [(k, ws[k]) for k in ['업무','재물','인간관계','연애·부부','가족','결정','이동','소비','기회','컨디션','휴식']]
        H.append(f'<section class="wk"><h2><span class="no">4</span>이번 주 종합점수 · <span style="color:{col(ws["종합"])}">{ws["종합"]} / 100</span></h2>'
                 '<h3>5. 영역별 주간 점수</h3><div class="areas">' + ''.join(f'<div class="area"><span>{k}</span><div class="tr"><div class="fl" style="width:{v}%;background:{col(v)}"></div></div><b style="color:{col(v)}">{v}</b></div>' for k, v in areas) + '</div></section>')
        def dd(date): return next(x for x in pp['days'] if x['date'] == date)
        cards = [('이번 주 최고의 날', pp['best'][0], 'good'), ('두 번째로 좋은 날', pp['best'][1], 'good'), ('가장 조심할 날', pp['worst'][0], 'bad'), ('두 번째로 조심할 날', pp['worst'][1], 'bad')]
        H.append('<section class="wk"><h2><span class="no">6</span>최고의 날 · 조심할 날</h2><div class="cards">' + ''.join(
            f'<div class="card {c}"><h4>{lab}</h4><p><b>{dd(x)["wd"]}요일 {int(x[5:7])}월 {int(x[8:])}일 · {dd(x)["gzk"]}일 · {dd(x)["scores"]["종합"]}점</b></p><p>{E((dtexts.get(x, {}) or {}).get("h") or default_h(dd(x)))}</p></div>' for lab, x, c in cards) + '</div></section>')
        ph = t.get('phases', {})
        if ph:
            H.append('<section class="wk"><h2>주간 흐름 3구간</h2><div class="pair">' + ''.join(f'<div><b>{E(k)}</b><span>{E(v)}</span></div>' for k, v in ph.items()) + '</div></section>')
        # 요일별
        for j, d in enumerate(pp['days']):
            tx = dtexts.get(d['date'], {})
            tg, L = domain_lines(pp, d); do, av = todo(d)
            mo = int(d['date'][5:7]); da = int(d['date'][8:])
            sc = d['scores']
            rows = ''.join(f'<tr><th>{k}</th><td class="num" style="color:{col(v)}">{v}</td></tr>' for k, v in [(k, sc[k]) for k in ['업무','재물','인간관계','연애·부부','가족','결정','이동','소비','기회','컨디션','종합']])
            dom = ''.join(f'<div><dt>{k}</dt><dd><b style="color:{col(v[0])}">{v[0]}</b> · {v[1]} {E(v[2])}</dd></div>' for k, v in L.items())
            slots = ''.join(f'<tr class="{"best" if s["slot"]==d["best_slot"] else "worst" if s["slot"]==d["worst_slot"] else ""}"><th>{s["slot"]}</th><td>{s["branches"]}</td><td>{"가장 좋은 시간" if s["slot"]==d["best_slot"] else "가장 조심할 시간" if s["slot"]==d["worst_slot"] else ("좋은 편" if s["v"]>0 else "평이" if s["v"]>-6 else "조금 무거움")}</td></tr>' for s in d['slots'])
            lot = ''
            if 'lotto' in d:
                lo = d['lotto']
                lot = (f'<div class="lotto"><div class="ball">{lo["number"]}</div><div><b>오늘의 숫자</b><p>오늘 필요한 오행: {lo["element"]} · {E(lo["why"])}</p>'
                       f'<p>하도수에서 {lo["element"]}에 해당하는 수({", ".join(map(str, lo["cands"]))}) 가운데, 오늘 일진의 육십갑자 순번({lo["rank"]}번째)으로 골랐어요. 앞선 날과 겹치지 않게 조정했어요.</p>'
                       f'<p>명리적 상징 적합도 {"★"*lo["stars"]}{"☆"*(5-lo["stars"])} <small>(당첨 확률이 아니라 그날 테마와의 어울림)</small></p></div></div>')
            hsay = tx.get('say', '')
            swn = f"<p class='note'>이날 {d['switch'][1]} 무렵 {d['switch'][0]} 절기로 월운이 바뀌어요.</p>" if d['switch'] else ''
            H.append(f'''<details class="day"{" open" if j==0 else ""}><summary><span class="dl"><b>{d["wd"]}</b><small>{mo}/{da}</small></span><span class="dg">{d["gzk"]}일</span><span class="dh">{E(tx.get("h") or default_h(d))}</span><span class="ds" style="color:{col(sc["종합"])}">{sc["종합"]}</span></summary>
<div class="dbody">
<p class="dkey"><b>1) 오늘의 한마디</b> {E(tx.get("h") or default_h(d))}</p>{swn}
<div class="dgrid"><div><h4>2) 오늘의 명리 구조</h4><p>년운 {d["year"]} · 월운 {d["month"]} · 일진 {d["gzk"]} ({d["sNat"]} / {d["bNat"]})</p><p>{E(tg)}</p><ul class="plain">{"".join(f"<li>{E(x)}</li>" for x in structure_lines(d))}</ul></div>
<div><h4>3) 오늘 종합점수 · <span style="color:{col(sc["종합"])}">{sc["종합"]}</span></h4><div class="tbl"><table><tbody>{rows}</tbody></table></div></div></div>
<h4>4)~12) 영역별 판단</h4><dl class="doms">{dom}</dl>
<div class="todo"><div class="y"><h4>13) 하면 좋은 것</h4><ul>{"".join(f"<li>{E(x)}</li>" for x in do)}</ul></div><div class="n"><h4>14) 피하면 좋은 것</h4><ul>{"".join(f"<li>{E(x)}</li>" for x in av)}</ul></div></div>
<h4>15) 시간대별 흐름</h4><div class="tbl"><table><thead><tr><th>시간</th><th>시진</th><th>흐름</th></tr></thead><tbody>{slots}</tbody></table></div>
<h4>16) 실제로 나타나기 쉬운 패턴 TOP 3</h4><ol class="plain">{"".join(f"<li>{E(x)}</li>" for x in patterns(d))}</ol>
{f'<blockquote class="dsay"><b>17) 현암 선생의 오늘 한마디</b> {E(hsay)}</blockquote>' if hsay else ''}
{lot}
</div></details>''')
        # 토요일 로또
        rowsL = ''.join(f'<tr><th>{d["wd"]}요일</th><td class="num"><b>{d["lotto"]["number"]}</b></td><td>{d["lotto"]["element"]} · {E(d["lotto"]["why"])}</td></tr>' for d in pp['days'][:6])
        dist = {}
        for d in pp['days'][:6]: dist[d['lotto']['element']] = dist.get(d['lotto']['element'], 0) + 1
        H.append(f'<section class="wk"><h2>이번 주 현암 선생 로또 6/45</h2><div class="tbl"><table><thead><tr><th>선정일</th><th>추천번호</th><th>핵심 명리 근거</th></tr></thead><tbody>{rowsL}</tbody></table></div>'
                 f'<div class="final">{" · ".join(str(n) for n in pp["lotto"])}</div>'
                 f'<p>오행 분포: {", ".join(f"{k} {v}개" for k, v in dist.items())}. 일요일부터 금요일까지 매일 하나씩 쌓은 조합이라 토요일에 바꾸지 않았어요. {E(t.get("lotto_note", ""))}</p>'
                 '<p class="note">이 번호는 사주와 해당 주간 운의 상징을 이용해 선정한 재미·참고용 조합이며, 실제 로또 당첨번호를 예측하거나 당첨확률을 높인다는 의미는 아니에요. 재물운이 좋다고 복권 당첨운이 높아지는 것도 아니에요.</p></section>')
        b = pp['bests']
        H.append('<section class="wk"><h2>이번 주 최종 결론</h2><div class="pair">' + ''.join(f'<div><b>{k}</b><span>{v}</span></div>' for k, v in [
            ('종합점수', f"{ws['종합']} / 100"), ('최고의 날', dd(pp['best'][0])['wd'] + '요일'), ('가장 조심할 날', dd(pp['worst'][0])['wd'] + '요일'),
            ('업무가 가장 좋은 날', b['업무'] + '요일'), ('재물이 가장 안정적인 날', b['재물'] + '요일'), ('인간관계가 가장 좋은 날', b['인간관계'] + '요일'),
            ('결정하기 가장 좋은 날', b['결정'] + '요일'), ('쉬는 것이 가장 필요한 날', b['휴식'] + '요일')]) + '</div></section>')
        st = t.get('strategy', [])
        if st: H.append('<section class="wk"><h2>이번 주 행동전략</h2><ol class="plain">' + ''.join(f'<li>{E(x)}</li>' for x in st) + '</ol></section>')
        fin = t.get('final', '')
        if fin: H.append(f'<blockquote class="saying">{E(fin)}<small>현암 선생의 주간 한마디</small></blockquote>')
        panes.append(f'<div class="person-pane" data-key="{key}"{"" if i==0 else " hidden"}><div class="wrap">' + '\n'.join(H) + '</div></div>')
    css = open(os.path.join(ROOT, 'tools', 'weekly.css')).read()
    page = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta name="robots" content="noindex, nofollow">
<title>현암 선생 주간운세 {s0.month}월 {s0.day}일 주</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Song+Myung&family=Nanum+Myeongjo:wght@400;700;800&family=IBM+Plex+Sans+KR:wght@400;500;600&display=swap">
<style>{css}</style></head><body>
<nav class="famnav" aria-label="가족 선택"><div class="in"><a class="brand" href="../index.html">우리 가족 사주</a><a class="back" href="index.html">주간운세 모음</a><div role="tablist">{"".join(tabs)}</div></div></nav>
{"".join(panes)}
<script>
(function(){{
  const panes=[...document.querySelectorAll(".person-pane")], tabs=[...document.querySelectorAll("[role=tab]")];
  function show(k){{ if(!panes.some(p=>p.dataset.key===k))k=panes[0].dataset.key; panes.forEach(p=>p.hidden=p.dataset.key!==k); tabs.forEach(t=>t.setAttribute("aria-selected",t.dataset.key===k?"true":"false")); try{{history.replaceState(null,"","#"+k)}}catch(e){{}} }}
  tabs.forEach(t=>t.addEventListener("click",()=>{{show(t.dataset.key);window.scrollTo({{top:0}})}}));
  const h=(location.hash||"").slice(1); if(h)show(h);
}})();
</script></body></html>'''
    assert not re.search(r'[一-鿿]', page), re.findall(r'.{10}[一-鿿].{5}', page)[:5]
    os.makedirs(os.path.join(ROOT, 'weekly'), exist_ok=True)
    open(os.path.join(ROOT, 'weekly', f'{sun}.html'), 'w').write(page)
    # 모음 목록
    items = []
    for f in sorted(os.listdir(os.path.join(ROOT, 'data')), reverse=True):
        m = re.match(r'week-(\d{4}-\d{2}-\d{2})\.json$', f)
        if not m: continue
        w = json.load(open(os.path.join(ROOT, 'data', f)))
        a = dt.date.fromisoformat(w['week_start']); b2 = dt.date.fromisoformat(w['week_end'])
        if not os.path.exists(os.path.join(ROOT, 'weekly', f'{m.group(1)}.html')): continue
        sc = ''.join(f'<span class="ps"><b>{x["name"]}</b><i style="color:{col(x["week_scores"]["종합"])}">{x["week_scores"]["종합"]}</i></span>' for x in w['people'])
        items.append(f'<a class="wkitem" href="{m.group(1)}.html"><span class="wr">{a.year}년 {a.month}월 {a.day}일 ~ {b2.month}월 {b2.day}일</span><span class="wp">{sc}</span></a>')
    idx = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta name="robots" content="noindex, nofollow">
<title>현암 선생 주간운세 모음</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Song+Myung&family=Nanum+Myeongjo:wght@400;700;800&family=IBM+Plex+Sans+KR:wght@400;500;600&display=swap">
<style>{css}</style></head><body>
<nav class="famnav"><div class="in"><a class="brand" href="../index.html">우리 가족 사주</a></div></nav>
<div class="wrap"><header class="wk-head"><div class="eyebrow">현암 선생 주간운세</div><h1>주간운세 모음</h1><div class="who">매주 일요일 아침, 아빠·엄마·딸 세 사람의 한 주를 새로 올려요. 숫자는 각 사람의 종합점수예요.</div></header>
<div class="wklist">{"".join(items)}</div>
<p class="note">로또 숫자는 명리 상징을 이용한 재미·참고용이며, 당첨을 예측하거나 확률을 높이지 않아요.</p></div></body></html>'''
    open(os.path.join(ROOT, 'weekly', 'index.html'), 'w').write(idx)
    print('rendered', sun, len(page))

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    render(sys.argv[1])
