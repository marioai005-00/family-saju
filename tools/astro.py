import math, datetime as dt
G="甲乙丙丁戊己庚辛壬癸"; Z="子丑寅卯辰巳午未申酉戌亥"
def jd(y,m,d,h=0.0):
    if m<=2: y-=1; m+=12
    A=y//100; B=2-A+A//4
    return int(365.25*(y+4716))+int(30.6001*(m+1))+d+B-1524.5+h/24
def sunlon(J):
    T=(J-2451545)/36525
    L0=280.46646+36000.76983*T+0.0003032*T*T
    M=math.radians(357.52911+35999.05029*T-0.0001537*T*T)
    C=(1.914602-0.004817*T-0.000014*T*T)*math.sin(M)+(0.019993-0.000101*T)*math.sin(2*M)+0.000289*math.sin(3*M)
    Om=math.radians(125.04-1934.136*T)
    return (L0+C-0.00569-0.00478*math.sin(Om))%360
def eot(J):  # minutes, apparent - mean
    T=(J-2451545)/36525
    L0=math.radians(280.46646+36000.76983*T); M=math.radians(357.52911+35999.05029*T)
    e=0.016708634-0.000042037*T; eps=math.radians(23.439291-0.0130042*T)
    y=math.tan(eps/2)**2
    E=y*math.sin(2*L0)-2*e*math.sin(M)+4*e*y*math.sin(M)*math.cos(2*L0)-0.5*y*y*math.sin(4*L0)-1.25*e*e*math.sin(2*M)
    return math.degrees(E)*4
def term(target, J0, dT=69):
    J=J0
    for _ in range(50):
        d=(target-sunlon(J)+540)%360-180
        J+=d/360*365.2422
        if abs(d)<1e-6: break
    J-=dT/86400  # TT->UT
    # to KST datetime
    k=J+9/24+0.5; Zi=int(k); F=k-Zi
    a=int((Zi-1867216.25)/36524.25); A=Zi+1+a-a//4; B=A+1524; C=int((B-122.1)/365.25); D=int(365.25*C); E=int((B-D)/30.6001)
    day=B-D-int(30.6001*E)+F; mo=E-1 if E<14 else E-13; yr=C-4716 if mo>2 else C-4715
    d=int(day); s=(day-d)*86400
    return dt.datetime(yr,mo,d)+dt.timedelta(seconds=round(s))
def daygz(y,m,d):
    i=(int(jd(y,m,d)+0.5)+49)%60
    return G[i%10]+Z[i%12], i
