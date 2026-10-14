"""Tablas de factores digitalizadas de las diapositivas del curso "Cimentaciones especiales".

Son las mismas tablas que usa el Excel (hojas "Factores" y "Tablas_PD"):
- Terzaghi (tabla de la diapositiva), Meyerhof (gráficas), Meyerhof 1953 (Fig. 12.4)
- λ de la NSR-98 (Figura H.4-5)
- Poulos y Davis: I0, RK, Rν y Rb (diapositivas 162–168)
"""
import math

# ---------------------------------------------------------------------------
# Terzaghi: tabla de la diapositiva "Carga por punta (Terzaghi)"
# phi: (Nc, Nq, Ng) falla general | (N'c, N'q, N'g) falla local
# ---------------------------------------------------------------------------
TERZAGHI_GENERAL = {
    0: (5.7, 1.0, 0.0), 5: (7.3, 1.6, 0.5), 10: (9.6, 2.7, 1.2), 15: (12.9, 4.4, 2.5),
    20: (17.7, 7.4, 5.0), 25: (25.1, 12.7, 9.7), 30: (37.2, 22.5, 19.7),
    35: (57.8, 41.4, 42.4), 40: (95.7, 81.3, 100.4), 45: (172.3, 173.3, 297.5),
}
TERZAGHI_LOCAL = {
    0: (5.7, 1.0, 0.0), 5: (6.7, 1.4, 0.2), 10: (8.0, 1.9, 0.5), 15: (9.7, 2.7, 0.9),
    20: (11.8, 3.9, 1.7), 25: (14.8, 5.6, 3.2), 30: (19.0, 8.3, 5.7),
    35: (25.2, 12.6, 10.1), 40: (34.9, 20.5, 18.8), 45: (51.2, 35.1, 37.7),
}

# ---------------------------------------------------------------------------
# Meyerhof (1951), cimentación profunda (beta = +90°): Npc, Npq, Npg
# digitalizados de las gráficas log de la diapositiva "Carga por punta (Meyerhof)"
# ---------------------------------------------------------------------------
MEYERHOF_NPC = {0: 10.0, 10: 21.0, 20: 68.0, 30: 280.0, 40: 1500.0, 50: 15000.0}
MEYERHOF_NPQ = {0: 1.0, 10: 3.0, 20: 22.0, 30: 165.0, 40: 1200.0, 50: 12500.0}
MEYERHOF_NPG = {0: 0.0, 5: 0.3, 10: 2.5, 20: 15.0, 30: 110.0, 40: 1150.0, 50: 16000.0}

# ---------------------------------------------------------------------------
# Meyerhof (1953) "simplificado": Nc y Nq (hincado / excavado)
# digitalizados de la Fig. 12.4 de la diapositiva "Meyerhof simplificado".
# Nc solo está graficado hasta 28°; por encima se extrapola en escala log.
# ---------------------------------------------------------------------------
M53_NC = {0: 10.5, 10: 30.0, 20: 70.0, 28: 250.0}
M53_NQ_HINCADO = {0: 1.0, 10: 4.0, 20: 19.0, 30: 118.0, 35: 350.0, 40: 1200.0, 45: 7700.0}
M53_NQ_EXCAVADO = {0: 1.0, 10: 3.5, 20: 14.0, 30: 76.0, 35: 204.0, 40: 600.0, 45: 3700.0}

# ---------------------------------------------------------------------------
# NSR-98 Figura H.4-5: coeficiente lambda vs profundidad de penetración L (m)
# ---------------------------------------------------------------------------
LAMBDA_TABLE = [(0, 0.5), (5, 0.336), (10, 0.245), (15, 0.2), (20, 0.173), (25, 0.15),
                (30, 0.136), (35, 0.132), (40, 0.127), (50, 0.118), (60, 0.113),
                (70, 0.11), (80, 0.11), (90, 0.11)]

# ---------------------------------------------------------------------------
# Poulos y Davis (1980) — asentamiento de pilote aislado
# ---------------------------------------------------------------------------
# Fig. 5.18: I0 vs L/d (db/d = 1, sin campana)
I0_TABLE = [(2.5, 0.35), (5, 0.21), (10, 0.14), (15, 0.105), (20, 0.087), (25, 0.074),
            (30, 0.064), (35, 0.057), (40, 0.052), (45, 0.047), (50, 0.043), (100, 0.0254)]

# Fig. 5.19: RK(L/d, K)
RK_K = [10, 30, 100, 300, 1000, 3000, 10000]
RK_LD = [1, 2, 5, 10, 25, 50, 100]
RK_TABLE = [
    [1.06, 1.03, 1.01, 1.00, 1.00, 1.00, 1.00],
    [1.12, 1.07, 1.03, 1.01, 1.00, 1.00, 1.00],
    [1.50, 1.27, 1.12, 1.05, 1.02, 1.01, 1.00],
    [2.22, 1.70, 1.33, 1.15, 1.06, 1.02, 1.00],
    [3.00, 2.85, 1.90, 1.45, 1.18, 1.06, 1.01],
    [3.00, 3.00, 2.85, 2.05, 1.48, 1.20, 1.07],
    [3.00, 3.00, 3.00, 3.00, 2.00, 1.42, 1.15],
]

# Fig. 5.21: Rv = R0 + (1 - R0)·v/0.5   (rectas)
RV_K = [100, 500, 1000, 2000]
RV_R0 = [0.875, 0.842, 0.832, 0.828]

# Rb(L/d, K, Eb/Es)   (pilote por punta)
RB_LD = [5, 10, 25, 50, 75]
RB_K = [100, 500, 1000, 5000, 20000]
RB_E = [1, 3, 10, 30, 100, 1000]
RB_TABLE = {  # (L/d, K): [valores para Eb/Es = 1, 3, 10, 30, 100, 1000]
    (5, 100): [1, 0.72, 0.48, 0.36, 0.28, 0.24],
    (5, 500): [1, 0.66, 0.36, 0.17, 0.09, 0.05],
    (5, 1000): [1, 0.65, 0.33, 0.15, 0.07, 0.03],
    (5, 5000): [1, 0.64, 0.31, 0.13, 0.04, 0.01],
    (5, 20000): [1, 0.63, 0.30, 0.12, 0.035, 0.005],
    (10, 100): [1, 0.76, 0.60, 0.50, 0.45, 0.43],
    (10, 500): [1, 0.69, 0.43, 0.27, 0.18, 0.14],
    (10, 1000): [1, 0.68, 0.39, 0.23, 0.13, 0.09],
    (10, 5000): [1, 0.665, 0.37, 0.19, 0.08, 0.02],
    (10, 20000): [1, 0.66, 0.36, 0.18, 0.06, 0.0],
    (25, 100): [1, 0.96, 0.91, 0.86, 0.83, 0.81],
    (25, 500): [1, 0.85, 0.66, 0.55, 0.51, 0.47],
    (25, 1000): [1, 0.83, 0.57, 0.42, 0.36, 0.30],
    (25, 5000): [1, 0.75, 0.50, 0.30, 0.12, 0.01],
    (25, 20000): [1, 0.75, 0.50, 0.30, 0.12, 0.01],
    (50, 100): [1, 0.98, 0.95, 0.93, 0.92, 0.92],
    (50, 500): [1, 0.93, 0.86, 0.80, 0.76, 0.73],
    (50, 1000): [1, 0.92, 0.81, 0.70, 0.62, 0.58],
    (50, 5000): [1, 0.89, 0.69, 0.45, 0.29, 0.20],
    (50, 20000): [1, 0.87, 0.63, 0.37, 0.17, 0.05],
    (75, 100): [1, 0.99, 0.98, 0.97, 0.96, 0.95],
    (75, 500): [1, 0.97, 0.94, 0.90, 0.88, 0.86],
    (75, 1000): [1, 0.95, 0.89, 0.83, 0.79, 0.75],
    (75, 5000): [1, 0.93, 0.79, 0.60, 0.46, 0.36],
    (75, 20000): [1, 0.92, 0.73, 0.47, 0.25, 0.12],
}


# ---------------------------------------------------------------------------
# Interpolación
# ---------------------------------------------------------------------------
def _interp_log_points(points, x):
    """Interpolación en log10(y) entre puntos (x, y); lineal si algún y = 0."""
    xs = sorted(points)
    x = min(max(x, xs[0]), xs[-1])
    for a, b in zip(xs[:-1], xs[1:]):
        if a <= x <= b:
            ya, yb = points[a], points[b]
            t = (x - a) / (b - a)
            if ya > 0 and yb > 0:
                return 10 ** (math.log10(ya) + t * (math.log10(yb) - math.log10(ya)))
            return ya + t * (yb - ya)
    return points[xs[-1]]


def _extrap_log(points, x):
    """Como _interp_log_points pero extrapola en log por encima del último punto."""
    xs = sorted(points)
    if x <= xs[-1]:
        return _interp_log_points(points, x)
    a, b = xs[-2], xs[-1]
    slope = (math.log10(points[b]) - math.log10(points[a])) / (b - a)
    return 10 ** (math.log10(points[b]) + slope * (x - b))


def factor_table_1deg():
    """Tabla de trabajo cada 1° (0–45°) con todas las columnas de factores.

    Columnas: phi, Nc_Tg, Nq_Tg, Ng_Tg, Nc_Tl, Nq_Tl, Ng_Tl, Npc, Npq, Npg,
              Nc53, Nq53_hincado, Nq53_excavado
    """
    rows = []
    tg = {k: v for k, v in TERZAGHI_GENERAL.items()}
    tl = {k: v for k, v in TERZAGHI_LOCAL.items()}
    for phi in range(0, 46):
        r = [phi]
        for tab in (tg, tl):
            for j in range(3):
                r.append(_interp_log_points({k: v[j] for k, v in tab.items()}, phi))
        r.append(_interp_log_points(MEYERHOF_NPC, phi))
        r.append(_interp_log_points(MEYERHOF_NPQ, phi))
        r.append(_interp_log_points(MEYERHOF_NPG, phi))
        r.append(_extrap_log(M53_NC, phi))
        r.append(_interp_log_points(M53_NQ_HINCADO, phi))
        r.append(_interp_log_points(M53_NQ_EXCAVADO, phi))
        rows.append([round(v, 4) if i else v for i, v in enumerate(r)])
    return rows


FACTOR_COLUMNS = ["φ (°)", "Nc Terzaghi general", "Nq Terzaghi general", "Nγ Terzaghi general",
                  "Nc Terzaghi local", "Nq Terzaghi local", "Nγ Terzaghi local",
                  "Npc Meyerhof", "Npq Meyerhof", "Npγ Meyerhof",
                  "Nc Meyerhof 1953", "Nq 1953 hincado", "Nq 1953 excavado"]


FACTORES = factor_table_1deg()  # tabla cada 1° que usan los cálculos
