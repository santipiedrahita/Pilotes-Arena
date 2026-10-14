"""Motor de cálculo: capacidad portante y asentamiento de un pilote individual en arenas.

Sigue exactamente el mismo procedimiento del Excel "Capacidad_Portante_Pilote_v6.xlsx":
  1. Fuste por estratos, solo hasta Lf = mín(L, 15D), con 5 métodos:
     pág. 117 (Mohr-Coulomb), α, β, λ y ρ (NSR-98 H.4.1.5.3, con Nq y Nc de Janbu).
  2. Punta en z = L con 4 métodos: Terzaghi, Meyerhof, Meyerhof simplificado y NSR-98 H.4-6 (Janbu).
  3. Qadm = Qp/FSp + Qs/FSs; si Qu/Qadm < FS mínimo → Qadm = Qu/FS mínimo.
  4. Asentamiento de pilote por punta (Poulos y Davis): δ = P·I/(Es·d), I = I0·RK·Rb·Rν.

Unidades: kN, m, kPa.
"""
import math
from dataclasses import dataclass, field

import tablas as T

METODOS_FUSTE = ["Pág. 117", "α", "β", "λ", "ρ"]
METODOS_PUNTA = ["Terzaghi", "Meyerhof", "Meyerhof simplificado", "NSR-98 H.4-6"]

# Columnas de la tabla de factores cada 1° (tablas.FACTORES)
_COL = {"Nc_Tg": 1, "Nq_Tg": 2, "Ng_Tg": 3, "Nc_Tl": 4, "Nq_Tl": 5, "Ng_Tl": 6,
        "Npc": 7, "Npq": 8, "Npg": 9, "Nc53": 10, "Nq53_hincado": 11, "Nq53_excavado": 12}


# ---------------------------------------------------------------------------
# Datos de entrada
# ---------------------------------------------------------------------------
@dataclass
class Estrato:
    descripcion: str
    espesor: float          # m
    c: float                # kPa
    phi: float              # °
    gamma: float            # kN/m³ (sobre el NF)
    gamma_sat: float        # kN/m³ (bajo el NF)
    ocr: float = 1.0
    compacidad: str = "Suelta"   # "Suelta" → η = π/3 ; "Densa" → η = 0.58π
    eta: float | None = None     # η manual (rad); None → según compacidad
    E: float = 30000.0      # kPa (asentamiento)
    nu: float = 0.30        # (asentamiento)

    @property
    def eta_usado(self):
        if self.eta is not None:
            return self.eta
        return 0.58 * math.pi if self.compacidad == "Densa" else math.pi / 3


@dataclass
class Datos:
    # Pilote y sitio
    D: float = 0.40
    L: float = 12.0
    tipo: str = "Hincado"            # "Hincado" | "Preexcavado"
    NF: float = 4.0
    gamma_w: float = 9.81
    FSp: float = 3.0
    FSs: float = 2.0
    FS_min: float = 2.5
    # Métodos y coeficientes
    metodo_fuste: str = "ρ"
    metodo_punta: str = "NSR-98 H.4-6"
    falla_terzaghi: str = "General"  # "General" | "Local"
    ca_c: float = 1.0                # pág. 117: ca / c
    ks_K0: float | None = None       # pág. 117: ks / K0 (None → 1.4 hincado, 1.0 preexcavado)
    factor_tan: float = 2.0 / 3.0    # tanφa / tanφ (pág. 117 y β)
    coef_rho: float | None = None    # ρ: 0.11 hincado, 0.045 preexcavado (None → automático)
    # Asentamiento
    Ep: float = 25_000_000.0         # kPa
    P: float | None = None           # kN (None → Qadm)
    manual: dict = field(default_factory=dict)  # valores leídos a mano: {"I0":…, "RK":…, "Rb":…, "Rν":…}
    estratos: list = field(default_factory=list)

    # Derivados ------------------------------------------------------------
    @property
    def Ap(self):
        return math.pi * self.D ** 2 / 4

    @property
    def perimetro(self):
        return math.pi * self.D

    @property
    def Lf(self):
        return min(self.L, 15 * self.D)

    @property
    def ks_K0_usado(self):
        if self.ks_K0 is not None:
            return self.ks_K0
        return 1.4 if self.tipo == "Hincado" else 1.0

    @property
    def coef_rho_usado(self):
        if self.coef_rho is not None:
            return self.coef_rho
        return 0.11 if self.tipo == "Hincado" else 0.045


def ejemplo():
    """El mismo ejemplo del Excel."""
    return Datos(estratos=[
        Estrato("Arena limosa suelta", 3.0, 5, 28, 17.0, 18.5, 1.0, "Suelta", None, 30000, 0.30),
        Estrato("Arena fina suelta", 4.0, 0, 32, 18.5, 19.5, 1.0, "Suelta", None, 40000, 0.30),
        Estrato("Arena media densa", 4.0, 0, 35, 19.5, 20.5, 1.0, "Densa", None, 75000, 0.32),
        Estrato("Arena gruesa densa", 6.0, 0, 38, 20.0, 21.0, 1.0, "Densa", None, 90000, 0.35),
    ])


# ---------------------------------------------------------------------------
# Herramientas
# ---------------------------------------------------------------------------
def factor(nombre, phi):
    """Factor de la tabla cada 1°, interpolado linealmente (igual que el Excel)."""
    p = min(max(phi, 0.0), 44.999)
    i = int(p)
    a = T.FACTORES[i][_COL[nombre]]
    b = T.FACTORES[i + 1][_COL[nombre]]
    return a + (p - i) * (b - a)


def janbu(phi, eta):
    """Nq y Nc de Janbu (diapositiva 134, ec. 8.14 y 8.15)."""
    t = math.tan(math.radians(phi))
    nq = (t + math.sqrt(1 + t * t)) ** 2 * math.exp(2 * eta * t)
    nc = 2 * (1 + eta) if phi == 0 else (nq - 1) / t
    return nq, nc


def lambda_nsr(L):
    """λ de la NSR-98 Figura H.4-5 (interpolación lineal según L)."""
    x = min(L, 89.999)
    tab = T.LAMBDA_TABLE
    for (x0, y0), (x1, y1) in zip(tab[:-1], tab[1:]):
        if x0 <= x < x1:
            return y0 + (x - x0) * (y1 - y0) / (x1 - x0)
    return tab[-1][1]


def _pos(xs, x):
    """Equivalente a MATCH(x, xs, 1): índice del último xs[i] ≤ x (base 0)."""
    i = 0
    for k, v in enumerate(xs):
        if v <= x:
            i = k
    return i


def _frac_lin(xs, x, i):
    return (x - xs[i]) / (xs[i + 1] - xs[i])


def _frac_log(xs, x, i):
    return (math.log10(x) - math.log10(xs[i])) / (math.log10(xs[i + 1]) - math.log10(xs[i]))


# ---------------------------------------------------------------------------
# Estratigrafía y esfuerzos
# ---------------------------------------------------------------------------
def perfil(d: Datos):
    """Techo, base, partes seca/saturada y σ'v en el techo de cada estrato."""
    filas = []
    techo, sv_techo = 0.0, 0.0
    for e in d.estratos:
        base = techo + e.espesor
        h_seco = max(0.0, min(base, d.NF) - techo)
        h_sat = (base - techo) - h_seco
        filas.append(dict(estrato=e, techo=techo, base=base, h_seco=h_seco, h_sat=h_sat, sv_techo=sv_techo))
        sv_techo += e.gamma * h_seco + (e.gamma_sat - d.gamma_w) * h_sat
        techo = base
    return filas


def sigma_v(d: Datos, f, z):
    """σ'v a la profundidad z dentro del estrato f (dict de perfil)."""
    e = f["estrato"]
    return (f["sv_techo"] + e.gamma * max(0.0, min(z, d.NF) - f["techo"])
            + (e.gamma_sat - d.gamma_w) * max(0.0, z - max(d.NF, f["techo"])))


def estrato_en(prf, z):
    """Estrato que contiene la profundidad z (si z está en un límite, el de abajo)."""
    idx = 0
    for k, f in enumerate(prf):
        if f["techo"] <= z:
            idx = k
    return idx


# ---------------------------------------------------------------------------
# 1. Fuste
# ---------------------------------------------------------------------------
def fuste(d: Datos, prf):
    lam = lambda_nsr(d.L)
    C = d.perimetro
    filas = []
    tot = {m: 0.0 for m in METODOS_FUSTE}
    for k, f in enumerate(prf):
        e = f["estrato"]
        desde, hasta = min(f["techo"], d.Lf), min(f["base"], d.Lf)
        h = hasta - desde
        fila = dict(n=k + 1, descripcion=e.descripcion, desde=desde, hasta=hasta, h=h)
        if h <= 0:
            filas.append(fila)
            continue
        s_desde, s_hasta = sigma_v(d, f, desde), sigma_v(d, f, hasta)
        n = min(max(d.NF, desde), hasta)          # punto donde el NF corta el tramo (si lo corta)
        s_n = sigma_v(d, f, n)
        s_prom = ((n - desde) * (s_desde + s_n) + (hasta - n) * (s_n + s_hasta)) / (2 * h)
        phi = math.radians(e.phi)
        K0 = (1 - math.sin(phi)) * math.sqrt(e.ocr)
        tan_a = d.factor_tan * math.tan(phi)
        # Pág. 117: fs = ca + ks·σ'v·tanφa
        ks = d.ks_K0_usado * K0
        ca = d.ca_c * e.c
        fs117 = ca + ks * s_prom * tan_a
        # α: fs = α·su
        su = e.c
        alfa = 1.0 if su <= 25 else (1 - (su - 25) / 90 if su < 70 else 0.5)
        fs_a = alfa * su
        # β: fs = β·qv, β = K0·tanφa
        beta = K0 * tan_a
        fs_b = beta * s_prom
        # λ: fs = λ(qv + 2su)
        fs_l = lam * (s_prom + 2 * su)
        # ρ: fs = ρ·q0, q0 = c·Nc + σ'v·Nq (Janbu)
        rho = d.coef_rho_usado * 10 ** (-1.3 * math.tan(phi))
        nq, nc = janbu(e.phi, e.eta_usado)
        q0 = e.c * nc + s_prom * nq
        fs_r = rho * q0
        fs_m = {"Pág. 117": fs117, "α": fs_a, "β": fs_b, "λ": fs_l, "ρ": fs_r}
        qs_m = {m: v * C * h for m, v in fs_m.items()}
        for m in tot:
            tot[m] += qs_m[m]
        fila.update(sv_desde=s_desde, sv_hasta=s_hasta, sv_prom=s_prom, K0=K0, tan_a=tan_a,
                    ks=ks, ca=ca, su=su, alfa=alfa, beta=beta, rho=rho, eta=e.eta_usado, Nq=nq, Nc=nc, q0=q0,
                    fs=fs_m, Qs=qs_m)
        filas.append(fila)
    return dict(filas=filas, Qs=tot, lam=lam)


# ---------------------------------------------------------------------------
# 2. Punta
# ---------------------------------------------------------------------------
def punta(d: Datos, prf):
    k = estrato_en(prf, d.L)
    f = prf[k]
    e = f["estrato"]
    c, phi = e.c, e.phi
    g = (e.gamma_sat - d.gamma_w) if d.L > d.NF else e.gamma
    sv = sigma_v(d, f, d.L)
    Ks = (1 - math.sin(math.radians(phi))) * math.sqrt(e.ocr)
    B2 = d.D / 2
    gen = d.falla_terzaghi == "General"
    res = {}
    # Terzaghi
    Nc, Nq, Ng = (factor("Nc_Tg" if gen else "Nc_Tl", phi), factor("Nq_Tg" if gen else "Nq_Tl", phi),
                  factor("Ng_Tg" if gen else "Ng_Tl", phi))
    res["Terzaghi"] = dict(Nc=Nc, Nq=Nq, Ng=Ng, qp=1.2 * c * Nc + sv * Nq + 0.6 * g * B2 * Ng,
                           ecuacion="qp = 1.2·c·Nc + σ'v·Nq + 0.6·γ·(B/2)·Nγ")
    # Meyerhof
    Nc, Nq, Ng = factor("Npc", phi), factor("Npq", phi), factor("Npg", phi)
    res["Meyerhof"] = dict(Nc=Nc, Nq=Nq, Ng=Ng, qp=c * Nc + sv * Nq + g * B2 * Ng,
                           ecuacion="qp = c·Npc + σo·Npq + γ·(B/2)·Npγ")
    # Meyerhof simplificado (1953)
    Nc = factor("Nc53", phi)
    Nq = factor("Nq53_hincado" if d.tipo == "Hincado" else "Nq53_excavado", phi)
    res["Meyerhof simplificado"] = dict(Nc=Nc, Nq=Nq, Ng=None, qp=c * Nc + Ks * sv * Nq,
                                        ecuacion="qp = c·Nc + Ks·σ'v·Nq")
    # NSR-98 H.4-6 con Janbu
    Nq, Nc = janbu(phi, e.eta_usado)
    res["NSR-98 H.4-6"] = dict(Nc=Nc, Nq=Nq, Ng=None, qp=c * Nc + sv * Nq,
                               ecuacion="qo = c·Nc + qvo·Nq (Janbu)")
    for m in res:
        res[m]["Qp"] = res[m]["qp"] * d.Ap
    return dict(metodos=res, estrato=k + 1, c=c, phi=phi, gamma=g, sv=sv, Ks=Ks, eta=e.eta_usado)


# ---------------------------------------------------------------------------
# 3. Carga admisible
# ---------------------------------------------------------------------------
def admisible(Qp, Qs, d: Datos):
    Qu = Qp + Qs
    parcial = Qp / d.FSp + Qs / d.FSs
    FSg = Qu / parcial if parcial > 0 else float("inf")
    usa_min = FSg < d.FS_min
    Qadm = Qu / d.FS_min if usa_min else parcial
    return dict(Qu=Qu, Qp_FS=Qp / d.FSp, Qs_FS=Qs / d.FSs, parcial=parcial, FSg=FSg,
                usa_min=usa_min, Qadm=Qadm)


# ---------------------------------------------------------------------------
# 4. Asentamiento (Poulos y Davis, pilote por punta)
# ---------------------------------------------------------------------------
def asentamiento(d: Datos, prf, P, k_punta):
    tramos = []
    sEh = sNh = sh = 0.0
    for k, f in enumerate(prf):
        h = max(0.0, min(f["base"], d.L) - f["techo"])
        e = f["estrato"]
        tramos.append(dict(n=k + 1, h=h, E=e.E, nu=e.nu))
        sEh += e.E * h
        sNh += e.nu * h
        sh += h
    Es = sEh / sh
    nus = sNh / sh
    Eb = prf[k_punta - 1]["estrato"].E
    RA = d.Ap / (math.pi * d.D ** 2 / 4)
    LD = d.L / d.D
    K = d.Ep * RA / Es
    EbEs = Eb / Es

    # I0 (lineal en L/d)
    xs, ys = [p[0] for p in T.I0_TABLE], [p[1] for p in T.I0_TABLE]
    x = min(max(LD, 2.5), 99.999)
    i = _pos(xs, x)
    I0 = ys[i] + _frac_lin(xs, x, i) * (ys[i + 1] - ys[i])

    # RK (lineal en L/d, logarítmico en K)
    xl, xk = min(max(LD, 1), 99.999), min(max(K, 10), 9999.99)
    i, j = _pos(T.RK_LD, xl), _pos(T.RK_K, xk)
    t, s = _frac_lin(T.RK_LD, xl, i), _frac_log(T.RK_K, xk, j)
    R = T.RK_TABLE
    RK = (1 - t) * ((1 - s) * R[i][j] + s * R[i][j + 1]) + t * ((1 - s) * R[i + 1][j] + s * R[i + 1][j + 1])

    # Rb (lineal en L/d, logarítmico en K y en Eb/Es)
    xl, xk, xe = min(max(LD, 5), 74.999), min(max(K, 100), 19999.9), min(max(EbEs, 1), 999.99)
    i, j, kk = _pos(T.RB_LD, xl), _pos(T.RB_K, xk), _pos(T.RB_E, xe)
    t, s, u = _frac_lin(T.RB_LD, xl, i), _frac_log(T.RB_K, xk, j), _frac_log(T.RB_E, xe, kk)

    def v(a, b):
        fila = T.RB_TABLE[(T.RB_LD[a], T.RB_K[b])]
        return fila[kk] + u * (fila[kk + 1] - fila[kk])
    Rb = (1 - t) * ((1 - s) * v(i, j) + s * v(i, j + 1)) + t * ((1 - s) * v(i + 1, j) + s * v(i + 1, j + 1))

    # Rν (rectas: Rν = R0 + (1 − R0)·ν/0.5, R0 logarítmico en K)
    xk = min(max(K, 100), 1999.99)
    j = _pos(T.RV_K, xk)
    R0 = T.RV_R0[j] + _frac_log(T.RV_K, xk, j) * (T.RV_R0[j + 1] - T.RV_R0[j])
    Rv = R0 + (1 - R0) * min(nus, 0.5) / 0.5

    grafica = {"I0": I0, "RK": RK, "Rb": Rb, "Rν": Rv}
    usado = {k: (d.manual.get(k) if d.manual.get(k) not in (None, 0) else v) for k, v in grafica.items()}
    I = usado["I0"] * usado["RK"] * usado["Rb"] * usado["Rν"]
    delta = P * I / (Es * d.D)
    return dict(tramos=tramos, Es=Es, nus=nus, Eb=Eb, RA=RA, LD=LD, K=K, EbEs=EbEs,
                grafica=grafica, usado=usado, I=I, P=P, delta_m=delta, delta_mm=delta * 1000)


# ---------------------------------------------------------------------------
# Cálculo completo
# ---------------------------------------------------------------------------
def validar(d: Datos):
    errores = []
    if not d.estratos:
        errores.append("Ingrese al menos un estrato.")
    if d.D <= 0 or d.L <= 0:
        errores.append("D y L deben ser mayores que cero.")
    for k, e in enumerate(d.estratos, 1):
        if e.espesor <= 0:
            errores.append(f"El estrato {k} tiene espesor cero o negativo.")
        if not (0 <= e.phi <= 45):
            errores.append(f"El φ del estrato {k} debe estar entre 0° y 45°.")
        if e.E <= 0:
            errores.append(f"El módulo E del estrato {k} debe ser mayor que cero.")
        if e.gamma <= 0:
            errores.append(f"El peso unitario γ del estrato {k} debe ser mayor que cero.")
    # γsat solo se usa en la parte del estrato que queda bajo el nivel freático
    for k, f in enumerate(perfil(d), 1):
        e = f["estrato"]
        if f["h_sat"] > 0 and e.gamma_sat <= d.gamma_w:
            errores.append(
                f"El estrato {k} queda (total o parcialmente) bajo el nivel freático, pero su γsat = "
                f"{e.gamma_sat:g} kN/m³ no es mayor que γw = {d.gamma_w:g}. Ingrese el peso unitario saturado "
                f"(p. ej. 18–21 kN/m³ en arenas); con este valor γ' = γsat − γw sería negativo o cero.")
    total = sum(e.espesor for e in d.estratos)
    avisos = []
    if d.estratos and d.L >= total:
        avisos.append(f"La longitud del pilote (L = {d.L:g} m) es mayor o igual que el perfil "
                      f"({total:g} m): la punta se toma en el último estrato.")
    return errores, avisos


def calcular(d: Datos):
    prf = perfil(d)
    fu = fuste(d, prf)
    pu = punta(d, prf)
    Qs_sel = fu["Qs"][d.metodo_fuste]
    Qp_sel = pu["metodos"][d.metodo_punta]["Qp"]
    adm = admisible(Qp_sel, Qs_sel, d)
    matriz_Qu = {pm: {fm: pu["metodos"][pm]["Qp"] + fu["Qs"][fm] for fm in METODOS_FUSTE} for pm in METODOS_PUNTA}
    matriz_Qadm = {pm: {fm: admisible(pu["metodos"][pm]["Qp"], fu["Qs"][fm], d)["Qadm"] for fm in METODOS_FUSTE}
                   for pm in METODOS_PUNTA}
    P = d.P if d.P is not None else adm["Qadm"]
    ase = asentamiento(d, prf, P, pu["estrato"])
    return dict(perfil=prf, fuste=fu, punta=pu, Qs=Qs_sel, Qp=Qp_sel, adm=adm,
                matriz_Qu=matriz_Qu, matriz_Qadm=matriz_Qadm, asentamiento=ase)


if __name__ == "__main__":
    r = calcular(ejemplo())
    print("Qs:", {k: round(v, 2) for k, v in r["fuste"]["Qs"].items()})
    print("Qp:", {k: round(v["Qp"], 2) for k, v in r["punta"]["metodos"].items()})
    print("Qadm:", round(r["adm"]["Qadm"], 2), " δ (mm):", round(r["asentamiento"]["delta_mm"], 3))
