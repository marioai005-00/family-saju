"""가족 주간운세 계산 엔진.

사용법:  python3 tools/weekly_engine.py 2026-10-04
  (일요일 날짜를 주면 그 주 일~토 7일을 계산해 data/주간-YYYY-MM-DD.json 으로 저장)

원국 → 대운 → 세운 → 월운 → 일진 순서로 겹쳐 점수와 작용을 계산한다.
숫자 선정은 하도수(1·6 물, 2·7 불, 3·8 나무, 4·9 쇠, 5·10 흙; 끝자리 0은 10으로 봄) 체계를 쓴다.
출력 문자열에는 한자를 쓰지 않는다(내부 계산용 한자 키만 사용).
"""
import sys, os, json, math, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from astro import term, jd, daygz, G, Z

GK = "갑을병정무기경신임계"; ZK = "자축인묘진사오미신유술해"
ANIMAL = ["쥐","소","호랑이","토끼","용","뱀","말","양","원숭이","닭","개","돼지"]
SNAT = {'甲':'큰 나무','乙':'풀·덩굴','丙':'하늘의 태양','丁':'등불','戊':'큰 땅','己':'논밭의 흙','庚':'큰 바위','辛':'작은 보석','壬':'큰 강','癸':'비·이슬'}
BNAT = {'子':'한겨울의 물','丑':'늦겨울 언 흙','寅':'초봄의 나무','卯':'한봄의 나무','辰':'늦봄 축축한 흙','巳':'초여름의 불','午':'한여름의 불','未':'늦여름 마른 흙','申':'초가을의 쇠','酉':'한가을의 쇠','戌':'늦가을 마른 흙','亥':'초겨울의 물'}
SEL = dict(zip("甲乙丙丁戊己庚辛壬癸", "木木火火土土金金水水"))
BEL = dict(zip("子丑寅卯辰巳午未申酉戌亥", "水土木木土火火土金金土水"))
BMAIN = dict(zip("子丑寅卯辰巳午未申酉戌亥", "癸己甲乙戊丙丁己庚辛戊壬"))
YANG = {s: (i % 2 == 0) for i, s in enumerate("甲乙丙丁戊己庚辛壬癸")}
ELK = {'木':'나무','火':'불','土':'흙','金':'쇠','水':'물'}
GEN = {'木':'火','火':'土','土':'金','金':'水','水':'木'}       # 생
CTRL = {'木':'土','土':'水','水':'火','火':'金','金':'木'}      # 극

def ko(gz): return GK[G.index(gz[0])] + ZK[Z.index(gz[1])]

def tengod(dm, s):
    a, b = SEL[dm], SEL[s]; same = YANG[dm] == YANG[s]
    if a == b: return '비견' if same else '겁재'
    if GEN[a] == b: return '식신' if same else '상관'
    if CTRL[a] == b: return '편재' if same else '정재'
    if CTRL[b] == a: return '편관' if same else '정관'
    if GEN[b] == a: return '편인' if same else '정인'
CAT = {'비견':'비겁','겁재':'비겁','식신':'식상','상관':'식상','편재':'재성','정재':'재성','편관':'관성','정관':'관성','편인':'인성','정인':'인성'}
TEN_E = {'비견':'나와 같은 기운','겁재':'경쟁하는 기운','식신':'꾸준히 만들어 내는 힘','상관':'틀을 깨는 표현','편재':'크게 움직이는 돈','정재':'차곡차곡 쌓는 돈','편관':'나를 누르는 압박','정관':'규칙과 질서','편인':'독특한 생각·직감','정인':'나를 돕고 보살피는 기운'}

CHUNG = {frozenset(p) for p in ['子午','丑未','寅申','卯酉','辰戌','巳亥']}
HAP = {frozenset(p) for p in ['子丑','寅亥','卯戌','辰酉','巳申','午未']}
PA = {frozenset(p) for p in ['子酉','丑辰','寅亥','卯午','巳申','未戌']}
HAE = {frozenset(p) for p in ['子未','丑午','寅巳','卯辰','申亥','酉戌']}
WON = {frozenset(p) for p in ['子未','丑午','寅酉','卯申','辰亥','巳戌']}
GWI = {frozenset(p) for p in ['子酉','丑午','寅未','卯申','辰亥','巳戌']}
HYUNG = {frozenset(p) for p in ['寅巳','巳申','丑戌','戌未','丑未','子卯']}
SAM = [('申子辰','水'),('亥卯未','木'),('寅午戌','火'),('巳酉丑','金')]
SHAP = {frozenset(p) for p in ['甲己','乙庚','丙辛','丁壬','戊癸']}
SCH = {frozenset(p) for p in ['甲庚','乙辛','丙壬','丁癸']}
YEOKMA = {'申':'寅','子':'寅','辰':'寅','寅':'申','午':'申','戌':'申','巳':'亥','酉':'亥','丑':'亥','亥':'巳','卯':'巳','未':'巳'}
ACTN = {'충':'정면 충돌','합':'손잡음','형':'꺾고 다듬음','파':'깨뜨림','해':'은근한 방해','원진':'괜히 불편함','귀문':'예민함','자형':'스스로 볶음','복음':'같은 글자 겹침'}

# ---------------- 사람 ----------------
PEOPLE = [
 dict(key='dad', name='아빠', sex='남', birth='1988-10-23 15:35 경기 성남 (진태양시 15:19)',
      pillars=['戊辰','壬戌','辛亥','丙申'],
      ev={'水':8,'木':6,'金':-1,'土':-6,'火':-5}, yong='水', hee='木', gi=['土','火'],
      excess=['土','火'], spouse='木',
      daewoon=[('1993-10-14','癸亥'),('2003-10-14','甲子'),('2013-10-14','乙丑'),('2023-10-14','丙寅'),('2033-10-14','丁卯'),('2043-10-14','戊辰')],
      seed=3),
 dict(key='mom', name='엄마', sex='여', birth='1973-09-30 오시 서울 (시각 미상, 경오시 가정)',
      pillars=['癸丑','辛酉','己巳','庚午'],
      ev={'火':8,'土':6,'木':0,'金':-6,'水':-5}, yong='火', hee='土', gi=['金','水'],
      excess=['金','水'], spouse='木',
      daewoon=[('1976-07-08','壬戌'),('1986-07-08','癸亥'),('1996-07-07','甲子'),('2006-07-08','乙丑'),('2016-07-07','丙寅'),('2026-07-08','丁卯'),('2036-07-07','戊辰')],
      seed=5),
 dict(key='daughter', name='딸', sex='여', birth='2013-05-01 18:23 서울 (진태양시 17:53)',
      pillars=['癸巳','丙辰','丁卯','己酉'],
      ev={'木':8,'火':6,'水':-1,'金':-6,'土':-4}, yong='木', hee='火', gi=['金','土'],
      excess=['金','土'], spouse='水',
      daewoon=[('2014-08-25','丁巳'),('2024-08-24','戊午'),('2034-08-24','己未'),('2044-08-24','庚申')],
      seed=7),
]
POSN = {'년':'원국 윗자리','월':'일터·사회 자리','일':'배우자·집 자리','시':'아랫사람·결과 자리','대운':'10년 흐름','세운':'올해','월운':'이달'}

# ---------------- 달력 ----------------
JIE = [('입춘',315,2,4),('경칩',345,3,6),('청명',15,4,5),('입하',45,5,6),('망종',75,6,6),('소서',105,7,7),('입추',135,8,8),('백로',165,9,8),('한로',195,10,8),('입동',225,11,7),('대설',255,12,7),('소한',285,1,5)]
_TCACHE = {}
def jie_times(y):
    if y in _TCACHE: return _TCACHE[y]
    out = []
    for i, (n, l, m, d) in enumerate(JIE):
        yy = y + 1 if m == 1 else y
        out.append((term(l, jd(yy, m, d)), n, i))
    _TCACHE[y] = out; return out
def year_gz(y): return G[(y - 4) % 10] + Z[(y - 4) % 12]
def pillars_at(t):
    """t(datetime, KST) 시점의 해·달 간지와 그 달의 시작 절기"""
    cands = []
    for y in (t.year - 1, t.year):
        for tt, n, i in jie_times(y): cands.append((tt, n, i, y))
    cands = [c for c in cands if c[0] <= t]; tt, n, i, sy = max(cands)
    ys = year_gz(sy)
    start = {'甲':2,'己':2,'乙':4,'庚':4,'丙':6,'辛':6,'丁':8,'壬':8,'戊':0,'癸':0}[ys[0]]
    mp = G[(start + i) % 10] + Z[(2 + i) % 12]
    return ys, mp, (tt, n)

def dw_at(p, d):
    cur = None
    for s, g in p['daewoon']:
        if dt.date.fromisoformat(s) <= d: cur = (s, g)
    return cur

# ---------------- 작용 ----------------
def branch_acts(b, P):
    acts = []
    for k, v in P.items():
        if b == v:
            acts.append(('자형' if b in '辰午酉亥' else '복음', k)); continue
        f = frozenset(b + v)
        if f in CHUNG: acts.append(('충', k))
        if f in HAP: acts.append(('합', k))
        if f in HYUNG: acts.append(('형', k))
        if f in PA and f not in HAP: acts.append(('파', k))
        if f in HAE: acts.append(('해', k))
        if f in WON: acts.append(('원진', k))
        if f in GWI: acts.append(('귀문', k))
    allb = set(P.values()); sams = []
    for tri, el in SAM:
        if b in tri:
            have = [c for c in tri if c != b and c in allb]
            if have: sams.append((el, '완성' if len(have) == 2 else '반합'))
    if b in '寅巳申' and all(c in allb or c == b for c in '寅巳申'): acts.append(('삼형', '인사신'))
    if b in '丑戌未' and all(c in allb or c == b for c in '丑戌未'): acts.append(('삼형', '축술미'))
    return acts, sams

def stem_acts(s, SP):
    out = []
    for k, v in SP.items():
        if s == v: continue
        f = frozenset(s + v)
        if f in SHAP: out.append(('합', k, v))
        if f in SCH: out.append(('충', k, v))
    return out

CW = {'충': {'일': -7, '월': -5, '년': -4, '시': -4, '대운': -3, '세운': -3, '월운': -3}, '합': 2, '형': -2, '파': -1, '해': -2, '원진': -1, '귀문': -1, '자형': -2, '복음': -1}

def layer_delta(p, gz, P, SP):
    s, b = gz; ev = p['ev']
    d = ev[SEL[s]] + ev[BEL[b]] * 1.1
    acts, sams = branch_acts(b, P)
    for k, pos in acts:
        if k == '삼형': d -= 5; continue
        w = CW[k]; d += w[pos] if isinstance(w, dict) else w
    for el, kind in sams: d += (ev[el] / 2) * (2 if kind == '완성' else 1)
    st = stem_acts(s, SP)
    for k, pos, v in st:
        if pos == '일간': d += -3 if k == '충' else -1
        elif k == '합' and SEL[v] == p['yong']: d -= 3
        elif k == '충' and SEL[s] == p['yong'] and SEL[v] in p['gi']: d += 2
        elif k == '충' and SEL[v] == p['yong']: d -= 2
    return d, acts, sams, st

# ---------------- 하루 계산 ----------------
SLOTS = [('06~09','卯','辰'),('09~12','巳','午'),('12~15','午','未'),('15~18','申','酉'),('18~21','酉','戌'),('21~24','亥','子')]
HADO = {'水':[1,6],'火':[2,7],'木':[3,8],'金':[4,9],'土':[5,0]}

def clamp(x, lo=18, hi=94): return int(max(lo, min(hi, round(x))))

def day_calc(p, d):
    t = dt.datetime(d.year, d.month, d.day, 12)
    ys, mp, (mt, mn) = pillars_at(t)
    # 같은 날 절기가 바뀌는지
    switch = None
    for y in (d.year - 1, d.year):
        for tt, n, i in jie_times(y):
            if tt.date() == d: switch = (tt, n)
    gz, _ = daygz(d.year, d.month, d.day)
    dws, dwg = dw_at(p, d)
    yp, mpp, dpp, hp = p['pillars']; dm = dpp[0]
    base = {'년': yp[1], '월': mpp[1], '일': dpp[1], '시': hp[1]}
    bst = {'년간': yp[0], '월간': mpp[0], '일간': dm, '시간': hp[0]}
    P1 = dict(base, 대운=dwg[1]); S1 = dict(bst, 대운간=dwg[0])
    yd, *_ = layer_delta(p, ys, P1, S1)
    P2 = dict(P1, 세운=ys[1]); S2 = dict(S1, 세운간=ys[0])
    md, *_ = layer_delta(p, mp, P2, S2)
    P3 = dict(P2, 월운=mp[1]); S3 = dict(S2, 월운간=mp[0])
    dd, acts, sams, st = layer_delta(p, gz, P3, S3)
    overall = 52 + 0.7 * (0.25 * yd + 0.45 * md + dd)
    s, b = gz
    ts, tb = tengod(dm, s), tengod(dm, BMAIN[b])
    cs, cb = CAT[ts], CAT[tb]
    ev = p['ev']
    has = lambda k, pos=None: any(a == k and (pos is None or q == pos) for a, q in acts)
    nch = sum(1 for a, _ in acts if a == '충')
    good = lambda el: ev[el] > 0
    cats = [cs, cb]
    els = [SEL[s], BEL[b]]
    def catv(c):  # 그 십성이 이 사람에게 반가운지
        for x in (s, BMAIN[b]):
            if CAT[tengod(dm, x)] == c: return ev[SEL[x]]
        return 0
    work = overall + (5 if has('합', '월') else 0) - (7 if has('충', '월') else 0) - (3 if has('형', '월') else 0)
    work += sum(3 if catv(c) > 0 else -3 for c in cats if c in ('관성', '인성', '식상'))
    money = overall + (6 if '재성' in cats and catv('재성') > 0 else -3 if '재성' in cats else 0) - (7 if '겁재' in (ts, tb) else 0)
    money += 4 if ('식상' in cats and good(GEN[SEL[dm]]) and good(CTRL[SEL[dm]])) else 0
    rel = overall + (4 if has('합', '년') or has('합', '시') else 0) - (4 if has('원진') or has('해') else 0) - (3 if '비겁' in cats and catv('비겁') <= 0 else 0) - (4 if has('충', '시') or has('충', '년') else 0)
    love = overall - (12 if has('충', '일') else 0) + (8 if has('합', '일') else 0) - (6 if has('해', '일') else 0) - (5 if has('원진', '일') else 0) - (3 if has('자형', '일') or has('복음', '일') else 0)
    love += (4 if p['spouse'] in els and good(p['spouse']) else -2 if p['spouse'] in els else 0)
    fam = overall + (4 if has('합', '년') else 0) - (5 if has('충', '년') else 0) - (3 if has('원진', '년') else 0) + (3 if '인성' in cats and catv('인성') > 0 else 0)
    dec = overall - 5 * nch - (8 if has('삼형') else 0) + (5 if p['yong'] in els else 0) - (4 if '인성' in cats and catv('인성') < 0 else 0)
    yk = {YEOKMA.get(base['년']), YEOKMA.get(base['일'])}
    move = overall - 4 * sum(1 for a, q in acts if a == '충' and q in ('일', '월')) - (6 if has('삼형') else 0) + (2 if b in yk else 0)
    spend = overall - (8 if '비겁' in cats else 0) - (4 if '식신' in (ts, tb) else 0) + (3 if '인성' in cats else 0)
    opp = overall + sum(6 for el, k in sams if good(el)) - sum(4 for el, k in sams if not good(el)) + (4 if '재성' in cats and catv('재성') > 0 else 0)
    cond = overall - 5 * sum(1 for e in els if e in p['excess']) - (4 if has('귀문') else 0) + (4 if p['yong'] in els else 0)
    rest = cond + (5 if '인성' in cats else 0) - (3 if '관성' in cats else 0)
    OFF = {'업무': {'관성': 3, '식상': 2, '인성': 1, '비겁': -2, '재성': 1},
           '인간관계': {'비겁': -2, '식상': -1, '인성': 2, '관성': -1, '재성': 1},
           '가족': {'인성': 3, '비겁': -2, '관성': -1},
           '결정': {'식상': 2, '인성': -3, '관성': -1, '재성': 1},
           '이동': {'식상': 2, '재성': 2, '인성': -2},
           '소비': {'재성': -3, '식상': -2, '인성': 2},
           '기회': {'식상': 2, '재성': 3, '관성': 1},
           '휴식': {'인성': 3, '비겁': 1, '관성': -3, '식상': -1}}
    tsc = [CAT[ts], CAT[tb]]
    def off(dom): return sum(OFF[dom].get(c, 0) for c in tsc)
    work += off('업무'); rel += off('인간관계'); fam += off('가족'); dec += off('결정'); move += off('이동'); spend += off('소비'); opp += off('기회'); rest += off('휴식')
    if p['sex'] == '남': love += 5 if ('재성' in tsc and catv('재성') > 0) else -2 if '재성' in tsc else 0
    else: love += 4 if ('관성' in tsc and catv('관성') >= 0) else -3 if '관성' in tsc else 0; love -= 3 if '상관' in (ts, tb) else 0
    strong = p['key'] == 'dad'
    cond += (-2 if strong else 2) if '비겁' in tsc else 0
    cal = CALIB.get(p['key'], {}).get(d.isoformat())
    if cal is not None:  # 이미 공개한 일진록 점수와 맞춤
        delta = cal - overall
        work += delta; money += delta; rel += delta; love += delta; fam += delta; dec += delta
        move += delta; spend += delta; opp += delta; cond += delta; rest += delta; overall = cal
    sc = dict(종합=clamp(overall), 업무=clamp(work), 재물=clamp(money), 인간관계=clamp(rel), 연애·부부=clamp(love), 가족=clamp(fam),
              결정=clamp(dec), 이동=clamp(move), 소비=clamp(spend), 기회=clamp(opp), 컨디션=clamp(cond), 휴식=clamp(rest))
    # 시간대
    slots = []
    for lab, b1, b2 in SLOTS:
        v = 0
        for hb in (b1, b2):
            v += ev[BEL[hb]]
            f1 = frozenset(hb + base['일']); f2 = frozenset(hb + b)
            if hb != base['일'] and f1 in CHUNG: v -= 8
            if hb != b and f2 in CHUNG: v -= 10
            if f1 in HAP: v += 4
            if f2 in HAP: v += 3
        slots.append(dict(slot=lab, branches=ZK[Z.index(b1)] + '·' + ZK[Z.index(b2)], v=v))
    best = max(slots, key=lambda x: x['v']); worst = min(slots, key=lambda x: x['v'])
    return dict(date=d.isoformat(), wd='일월화수목금토'[(d.weekday() + 1) % 7], gz=gz, gzk=ko(gz),
                year=ko(ys), month=ko(mp), month_h=mp, year_h=ys, dw=ko(dwg), dw_h=dwg,
                switch=(switch[1], switch[0].strftime('%H:%M')) if switch else None,
                ts=ts, tb=tb, sNat=SNAT[s], bNat=ANIMAL[Z.index(b)] + ' · ' + BNAT[b],
                els=[ELK[e] for e in els], acts=acts, sams=sams, st=[(k, pos, GK[G.index(v)]) for k, pos, v in st],
                scores=sc, slots=slots, best_slot=best['slot'], worst_slot=worst['slot'])

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIB = {}
_f = os.path.join(_root, 'data', 'ilji-dad-2026.json')
if os.path.exists(_f): CALIB['dad'] = json.load(open(_f))

# ---------------- 숫자 ----------------
# 선천수: 간지 → 수 (갑·기·자·오 9, 을·경·축·미 8, 병·신·인·신 7, 정·임·묘·유 6, 무·계·진·술 5, 사·해 4)
SCS = {}
for _chars, _v in [('甲己子午', 9), ('乙庚丑未', 8), ('丙辛寅申', 7), ('丁壬卯酉', 6), ('戊癸辰戌', 5), ('巳亥', 4)]:
    for _c in _chars: SCS[_c] = _v
def _kn(c): return GK[G.index(c)] if c in G else ZK[Z.index(c)]
def _wrap(x): return (x - 1) % 45 + 1
def _band(n): return min(n // 10, 4)   # 1~9, 10~19, 20~29, 30~39, 40~45

def pick_number(p, day, used, elcount, family=()):
    """그날의 숫자 1개.
    1단계: 그날 필요한 오행을 정한다 (용신·희신, 같은 기운이 세 번 넘게 몰리지 않게).
    2단계: 후보를 만든다. 간지→수는 선천수, 오행→수는 하도수(생수·성수) 하나씩만 쓴다.
           일진 윗글자 수, 아랫글자 수, 내 일간 수, 이달 아랫글자 수, 필요한 오행의 하도수를 여러 방식으로 엮는다.
    3단계: 이미 고른 번호, 같은 끝자리, 같은 번호대(1~9, 10번대 …)가 겹치지 않는 후보를 고른다.
    """
    s, b = day['gz']; ms, mb = day['month_h']
    els = [SEL[s], BEL[b]]
    if p['yong'] in els: need, why = p['yong'], '오늘 들어온 용신을 살리는 쪽'
    elif p['hee'] in els: need, why = p['hee'], '오늘 들어온 희신을 살리는 쪽'
    else: need, why = p['yong'], '오늘 부족한 용신으로 균형을 잡는 쪽'
    if elcount.get(need, 0) >= 3:
        need = p['hee'] if need == p['yong'] else p['yong']; why += ' (같은 기운이 세 번 이상 몰리지 않게 조정)'
    dm = p['pillars'][2][0]; db = p['pillars'][2][1]; hb_ = p['pillars'][3][1]
    vs, vb, vp, vm = SCS[s], SCS[b], SCS[dm], SCS[mb]
    vd, vh = SCS[db], SCS[hb_]
    h1, h2 = HADO[need][0], HADO[need][1] or 10
    N = lambda c: f"{_kn(c)}({SCS[c]})"
    E_ = ELK[need]
    raw = [
     (vs + vb + vp + h2, f"일진 {N(s)}+{N(b)} + 내 일간 {N(dm)} + {E_}의 성수 {h2}"),
     (vs * vb + h1,      f"일진 {N(s)}×{N(b)} + {E_}의 생수 {h1}"),
     (vs + vb + vp + vm + h1, f"일진 {N(s)}+{N(b)} + 내 일간 {N(dm)} + 이달 {N(mb)} + {E_}의 생수 {h1}"),
     (vb * h2 + vs,      f"일진 아랫글자 {N(b)}×{E_}의 성수 {h2} + 윗글자 {N(s)}"),
     (vp * h1 + vs + vb, f"내 일간 {N(dm)}×{E_}의 생수 {h1} + 일진 {N(s)}+{N(b)}"),
     (vs * h2 + vb + vm, f"일진 윗글자 {N(s)}×{E_}의 성수 {h2} + 아랫글자 {N(b)} + 이달 {N(mb)}"),
     (vs + vb + h1,      f"일진 {N(s)}+{N(b)} + {E_}의 생수 {h1}"),
     (vp * vb + h2,      f"내 일간 {N(dm)}×일진 아랫글자 {N(b)} + {E_}의 성수 {h2}"),
     (vd * vs + h1 + vp, f"내 배우자 자리 {N(db)}×일진 윗글자 {N(s)} + {E_}의 생수 {h1} + 내 일간 {N(dm)}"),
     (vh * vb + vd + h2, f"내 시지 {N(hb_)}×일진 아랫글자 {N(b)} + 배우자 자리 {N(db)} + {E_}의 성수 {h2}"),
     (vp + vd + vs + vb + vh + h1, f"내 일주 {N(dm)}+{N(db)} + 시지 {N(hb_)} + 일진 {N(s)}+{N(b)} + {E_}의 생수 {h1}"),
    ]
    # 사람마다 원국이 다르니, 후보를 고르는 출발점도 원국(일주)의 선천수로 돌린다
    rot = (vp + vd) % len(raw)
    raw = raw[rot:] + raw[:rot]
    good = day['scores']['종합'] >= 55
    order = raw if good else raw[2:] + raw[:2]   # 좋은 날은 성수(큰 수)부터, 무거운 날은 생수(균형)부터
    tails = {u % 10 for u in used}
    bands = {}
    for u in used: bands[_band(u)] = bands.get(_band(u), 0) + 1
    pick = None
    fam = set(family)
    for strict in (3, 2, 1, 0):
        for x, f in order:
            n = _wrap(x)
            if n in used: continue
            if strict >= 1 and bands.get(_band(n), 0) >= 2: continue
            if strict >= 2 and n % 10 in tails: continue
            if strict >= 3 and n in fam: continue
            pick = (n, x, f); break
        if pick: break
    n, x, f = pick
    formula = f"{f} = {x}" + (f", 45를 넘어 한 바퀴 돌려 {n}" if x > 45 else "")
    stars = 3 + (1 if p['yong'] in els or p['hee'] in els else 0) + (1 if day['scores']['종합'] >= 60 else 0) - (1 if day['scores']['종합'] < 40 else 0)
    return dict(number=n, element=E_, why=why, formula=formula, stars=max(1, min(5, stars)))

# ---------------- 주간 ----------------
def week(sun):
    days = [sun + dt.timedelta(i) for i in range(7)]
    out = dict(week_start=days[0].isoformat(), week_end=days[-1].isoformat(), people=[])
    family = []
    for p in PEOPLE:
        dl = [day_calc(p, d) for d in days]
        used = []; elc = {}
        for day in dl[:6]:
            pk = pick_number(p, day, used, elc, family)
            used.append(pk['number']); elc[{v: k for k, v in ELK.items()}[pk['element']]] = elc.get({v: k for k, v in ELK.items()}[pk['element']], 0) + 1
            day['lotto'] = pk
        keys = list(dl[0]['scores'].keys())
        wk = {k: round(sum(d['scores'][k] for d in dl) / 7) for k in keys}
        order = sorted(dl, key=lambda d: -d['scores']['종합'])
        def bestfor(k, rev=False): return max(dl, key=lambda d: d['scores'][k])['wd'] if not rev else min(dl, key=lambda d: d['scores'][k])['wd']
        out['people'].append(dict(key=p['key'], name=p['name'], sex=p['sex'], birth=p['birth'],
            pillars=[ko(x) for x in p['pillars']], yong=ELK[p['yong']], hee=ELK[p['hee']], gi=[ELK[x] for x in p['gi']],
            days=dl, week_scores=wk,
            best=[order[0]['date'], order[1]['date']], worst=[order[-1]['date'], order[-2]['date']],
            bests=dict(업무=bestfor('업무'), 재물=bestfor('재물'), 인간관계=bestfor('인간관계'), 결정=bestfor('결정'), 휴식=bestfor('컨디션', True)),
            lotto=sorted(used)))
        family += used
    return out

if __name__ == '__main__':
    sun = dt.date.fromisoformat(sys.argv[1])
    assert sun.weekday() == 6, '일요일 날짜를 넣어 주세요'
    res = week(sun)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, 'data', f'week-{sun.isoformat()}.json')
    json.dump(res, open(path, 'w'), ensure_ascii=False, indent=1)
    for pp in res['people']:
        print('==', pp['name'], pp['week_scores']['종합'], 'lotto', pp['lotto'])
        for d in pp['days']:
            print(d['date'][5:], d['wd'], d['gzk'], d['month'], d['switch'] or '', d['ts'], d['tb'], d['scores']['종합'], {k: v for k, v in d['scores'].items() if k != '종합'}, [a for a in d['acts']], d['sams'], d['st'], d.get('lotto', {}).get('number'), d['best_slot'], d['worst_slot'])
    print('saved', path)
