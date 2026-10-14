"""Aplicación Streamlit: capacidad portante y asentamiento de un pilote individual en arenas.

Ejecutar con:   streamlit run app.py
Usa los mismos métodos y criterios del Excel "Capacidad_Portante_Pilote_v6.xlsx".
"""
import io
import math

import altair as alt
import pandas as pd
import streamlit as st

import calculos as C

st.set_page_config(page_title="Pilotes en arena", layout="wide")

AZUL = "#2a78d6"
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]  # orden fijo: Pág. 117, α, β, λ, ρ

COLS = ["Descripción", "Espesor (m)", "c (kPa)", "φ (°)", "γ (kN/m³)", "γsat (kN/m³)", "OCR",
        "Compacidad", "η manual (rad)", "E (kPa)", "ν"]


def df_ejemplo():
    filas = []
    for e in C.ejemplo().estratos:
        filas.append([e.descripcion, e.espesor, e.c, e.phi, e.gamma, e.gamma_sat, e.ocr,
                      e.compacidad, "", e.E, e.nu])
    return pd.DataFrame(filas, columns=COLS)


if "estratos_df" not in st.session_state:
    st.session_state.estratos_df = df_ejemplo()
    st.session_state.editor_v = 0


def num(v, defecto=0.0):
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return defecto
        return float(v)
    except (TypeError, ValueError):
        return defecto


# =============================================================================
# BARRA LATERAL: datos del pilote, FS y métodos
# =============================================================================
sb = st.sidebar
sb.header("Datos de entrada")

sb.subheader("Pilote y sitio")
D = sb.number_input("Diámetro, D (m)", 0.05, 5.0, 0.40, 0.05, format="%.2f")
L = sb.number_input("Longitud embebida, L (m)", 0.5, 100.0, 12.0, 0.5, format="%.2f")
tipo = sb.selectbox("Tipo de pilote", ["Hincado", "Preexcavado"])
NF = sb.number_input("Profundidad del nivel freático, NF (m)", 0.0, 500.0, 4.0, 0.5, format="%.2f",
                     help="Encima del NF se usa γ; debajo, γ' = γsat − γw. Si no hay NF, escriba un valor "
                          "mayor que el perfil (p. ej. 100).")
gw = sb.number_input("Peso unitario del agua, γw (kN/m³)", 9.0, 10.5, 9.81, 0.01, format="%.2f")

sb.subheader("Métodos")
metodo_fuste = sb.selectbox("Método de fuste", C.METODOS_FUSTE, index=4,
                            help="Pág. 117 = fs = ca + ks·σ'v·tanφa. α, β, λ y ρ = NSR-98 H.4.1.5.3.")
metodo_punta = sb.selectbox("Método de punta", C.METODOS_PUNTA, index=3)

sb.subheader("Factores de seguridad")
FSp = sb.number_input("FS para la punta, FSp", 1.0, 10.0, 3.0, 0.5, format="%.1f")
FSs = sb.number_input("FS para el fuste, FSs", 1.0, 10.0, 2.0, 0.5, format="%.1f")
FSmin = sb.number_input("FS global mínimo (Qu/Qadm)", 1.0, 10.0, 2.5, 0.1, format="%.2f",
                        help="Si Qu / (Qp/FSp + Qs/FSs) es menor que este valor, Qadm = Qu / FS mínimo.")

with sb.expander("Coeficientes de los métodos"):
    falla = st.selectbox("Terzaghi: tipo de falla", ["General", "Local"],
                         help="Tabla de Terzaghi de la diapositiva: falla general (suelo resistente) o local.")
    ca_c = st.number_input("Pág. 117: ca / c (adherencia)", 0.0, 1.5, 1.0, 0.05, format="%.2f",
                           help="En arena limpia c = 0, entonces ca = 0 sin importar este factor.")
    ks_K0 = st.number_input("Pág. 117: ks / K0", 0.3, 3.0, 1.4 if tipo == "Hincado" else 1.0, 0.05,
                            format="%.2f", key=f"ks_{tipo}",
                            help="Valores usuales en arena (Das): preexcavado ≈ 1.0; hincado 1.4 a 1.8.")
    factor_tan = st.number_input("Factor tanφa / tanφ (pág. 117 y β)", 0.3, 1.0, 2 / 3, 0.01, format="%.3f",
                                 help="Ejemplo de clase: μ = tanφa = (2/3)·tanφ.")
    coef_rho = st.number_input("ρ: coeficiente", 0.01, 0.2, 0.11 if tipo == "Hincado" else 0.045, 0.005,
                               format="%.3f", key=f"rho_{tipo}",
                               help="NSR-98 H.4-25: 0.11 hincado; 0.03–0.06 preexcavado.")

sb.subheader("Asentamiento")
Ep = sb.number_input("Módulo del pilote, Ep (kPa)", 1.0e6, 3.0e8, 2.5e7, 1.0e6, format="%.0f",
                     help="Concreto: Ep ≈ 4700·√f'c (MPa). f'c = 28 MPa → ≈ 2.5×10⁷ kPa.")
usar_qadm = sb.radio("Carga sobre el pilote, P", ["Usar Qadm", "Escribir la carga"], horizontal=True)
P_manual = None
if usar_qadm == "Escribir la carga":
    P_manual = sb.number_input("P (kN)", 0.0, 1.0e6, 500.0, 10.0, format="%.1f")

sb.divider()
if sb.button("Cargar el ejemplo del Excel"):
    st.session_state.estratos_df = df_ejemplo()
    st.session_state.editor_v += 1
    st.rerun()

# =============================================================================
# ENCABEZADO Y ESTRATIGRAFÍA
# =============================================================================
st.title("Capacidad portante y asentamiento de un pilote en arena")
st.caption("Pilote individual · cálculo por estratos · Unidades: kN, m, kPa · "
           "Métodos de las diapositivas del curso y NSR-98 H.4.1.5")

st.subheader("1. Estratigrafía")
st.caption("Escriba los estratos de arriba hacia abajo. Use el botón **+** al final de la tabla para agregar "
           "estratos, o seleccione una fila y bórrela. η se calcula según la compacidad "
           "(suelta → π/3, densa → 0.58π); escriba un valor en «η manual» solo si quiere otro.")

editado = st.data_editor(
    st.session_state.estratos_df,
    key=f"editor_{st.session_state.editor_v}",
    num_rows="dynamic",
    hide_index=True,
    column_config={
        "Descripción": st.column_config.TextColumn(width="medium"),
        "Espesor (m)": st.column_config.NumberColumn(min_value=0.0, format="%.2f", required=True),
        "c (kPa)": st.column_config.NumberColumn(min_value=0.0, format="%.1f", default=0.0),
        "φ (°)": st.column_config.NumberColumn(min_value=0.0, max_value=45.0, format="%.1f", required=True),
        "γ (kN/m³)": st.column_config.NumberColumn(min_value=0.0, format="%.2f", required=True,
                                                   help="Peso unitario sobre el nivel freático"),
        "γsat (kN/m³)": st.column_config.NumberColumn(min_value=0.0, format="%.2f", required=True,
                                                      help="Peso unitario saturado (bajo el nivel freático)"),
        "OCR": st.column_config.NumberColumn(min_value=1.0, format="%.2f", default=1.0),
        "Compacidad": st.column_config.SelectboxColumn(options=["Suelta", "Densa"], default="Suelta",
                                                       required=True),
        "η manual (rad)": st.column_config.TextColumn(
            help="Déjelo vacío para usar π/3 (suelta) o 0.58π (densa). Escriba un número solo si quiere otro η."),
        "E (kPa)": st.column_config.NumberColumn(min_value=0.0, format="%.0f", required=True,
                                                 help="Arena (tabla 5.3): suelta 27 500–55 000; "
                                                      "media 55 000–70 000; densa 70 000–110 000 kPa"),
        "ν": st.column_config.NumberColumn(min_value=0.0, max_value=0.5, format="%.2f", default=0.30),
    },
)

estratos = []
for _, f in editado.iterrows():
    if num(f["Espesor (m)"]) <= 0:
        continue
    eta_m = f["η manual (rad)"]
    try:
        eta_m = float(str(eta_m).replace(",", ".")) if str(eta_m).strip() not in ("", "None", "nan") else None
    except ValueError:
        eta_m = None
    estratos.append(C.Estrato(
        descripcion=str(f["Descripción"]) if pd.notna(f["Descripción"]) else "",
        espesor=num(f["Espesor (m)"]), c=num(f["c (kPa)"]), phi=num(f["φ (°)"]),
        gamma=num(f["γ (kN/m³)"]), gamma_sat=num(f["γsat (kN/m³)"]), ocr=num(f["OCR"], 1.0) or 1.0,
        compacidad=f["Compacidad"] if f["Compacidad"] in ("Suelta", "Densa") else "Suelta",
        eta=None if (eta_m is None or eta_m <= 0) else eta_m,
        E=num(f["E (kPa)"]), nu=num(f["ν"], 0.3)))

manual = {k: st.session_state.get(f"man_{k}") for k in ["I0", "RK", "Rb", "Rν"]}
datos = C.Datos(D=D, L=L, tipo=tipo, NF=NF, gamma_w=gw, FSp=FSp, FSs=FSs, FS_min=FSmin,
                metodo_fuste=metodo_fuste, metodo_punta=metodo_punta, falla_terzaghi=falla,
                ca_c=ca_c, ks_K0=ks_K0, factor_tan=factor_tan, coef_rho=coef_rho,
                Ep=Ep, P=P_manual, manual=manual, estratos=estratos)

errores, avisos = C.validar(datos)
for a in avisos:
    st.warning(a)
if errores:
    for e in errores:
        st.error(e)
    st.stop()

R = C.calcular(datos)
FU, PU, ADM, ASE = R["fuste"], R["punta"], R["adm"], R["asentamiento"]


# ---- Perfil del suelo (gráfico) + tabla calculada
def grafico_perfil():
    prf = R["perfil"]
    total = prf[-1]["base"]
    capas = pd.DataFrame([dict(n=f"{k+1}. {f['estrato'].descripcion}", techo=f["techo"], base=f["base"],
                               medio=(f["techo"] + f["base"]) / 2, x0=0, x1=10)
                          for k, f in enumerate(prf)])
    tonos = ["#efe3c8", "#e2cfa5", "#d4bb84", "#c6a866", "#b8954d", "#a98338", "#9a7228", "#8b621b"]
    ydom = [max(total, L, 0) * 1.02, 0]
    base_y = alt.Y("techo:Q", scale=alt.Scale(domain=ydom), title="Profundidad (m)")
    rect = alt.Chart(capas).mark_rect(stroke="#ffffff", strokeWidth=1.5).encode(
        x=alt.X("x0:Q", scale=alt.Scale(domain=[0, 10]), axis=None), x2="x1:Q",
        y=base_y, y2="base:Q",
        color=alt.Color("n:N", scale=alt.Scale(range=tonos), legend=None),
        tooltip=[alt.Tooltip("n:N", title="Estrato"), alt.Tooltip("techo:Q", title="Techo (m)"),
                 alt.Tooltip("base:Q", title="Base (m)")])
    txt = alt.Chart(capas).mark_text(align="left", dx=4, fontSize=12, color="#3d3a33").encode(
        x=alt.value(6), y=alt.Y("medio:Q", scale=alt.Scale(domain=ydom)), text="n:N")
    pil = pd.DataFrame([dict(x0=6.6, x1=7.4, techo=0, base=L)])
    pilote = alt.Chart(pil).mark_rect(color="#6b6b6b").encode(
        x=alt.X("x0:Q", scale=alt.Scale(domain=[0, 10])), x2="x1:Q",
        y=alt.Y("techo:Q", scale=alt.Scale(domain=ydom)), y2="base:Q",
        tooltip=[alt.Tooltip("base:Q", title="L (m)")])
    lin = pd.DataFrame([dict(y=NF, et=f"NF = {NF:g} m", c="#2a78d6"),
                        dict(y=datos.Lf, et=f"Lf = mín(L, 15D) = {datos.Lf:g} m", c="#eb6834")])
    lin = lin[lin["y"] <= ydom[0]]
    reglas = alt.Chart(lin).mark_rule(strokeDash=[6, 4], strokeWidth=2).encode(
        y=alt.Y("y:Q", scale=alt.Scale(domain=ydom)),
        color=alt.Color("et:N", scale=alt.Scale(domain=list(lin["et"]), range=list(lin["c"])),
                        legend=alt.Legend(orient="bottom", title=None, symbolType="stroke",
                                          symbolStrokeWidth=2, symbolDash=[6, 4], labelLimit=300)))
    return (rect + txt + pilote + reglas).resolve_scale(color="independent").properties(height=330)


c1, c2 = st.columns([1, 1.4])
with c1:
    st.altair_chart(grafico_perfil())
with c2:
    st.markdown("**Perfil calculado**")
    st.dataframe(pd.DataFrame([{
        "Estrato": k + 1, "Techo (m)": f["techo"], "Base (m)": f["base"],
        "h sobre NF (m)": f["h_seco"], "h bajo NF (m)": f["h_sat"],
        "η (rad)": f["estrato"].eta_usado, "σ'v techo (kPa)": f["sv_techo"]}
        for k, f in enumerate(R["perfil"])]).style.format(precision=2), hide_index=True)
    st.caption(f"Área de la punta Ap = π·D²/4 = **{datos.Ap:.4f} m²** · Perímetro C = π·D = "
               f"**{datos.perimetro:.4f} m** · 15D = **{15*D:.2f} m** · "
               f"Longitud para fuste Lf = mín(L, 15D) = **{datos.Lf:.2f} m**")

# =============================================================================
# RESUMEN
# =============================================================================
st.subheader("2. Resultados")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric(f"Qs · {metodo_fuste}", f"{R['Qs']:,.1f} kN")
m2.metric(f"Qp · {metodo_punta}", f"{R['Qp']:,.1f} kN")
m3.metric("Qu = Qp + Qs", f"{ADM['Qu']:,.1f} kN")
m4.metric("Qadm", f"{ADM['Qadm']:,.1f} kN",
          help="Qp/FSp + Qs/FSs, o Qu/FS mínimo si el FS global resulta menor")
m5.metric("Asentamiento δ", f"{ASE['delta_mm']:.2f} mm", help=f"Con P = {ASE['P']:,.1f} kN")

t_fu, t_pu, t_adm, t_ase, t_gr, t_ec = st.tabs(
    ["Fuste", "Punta", "Carga admisible", "Asentamiento", "Gráficas", "Ecuaciones"])

# ---------------------------------------------------------------- FUSTE
with t_fu:
    st.markdown(f"Fuste calculado **por estrato**, solo hasta **Lf = mín(L, 15D) = {datos.Lf:.2f} m**. "
                "Si un estrato queda por debajo de Lf, no aporta.")
    filas = [f for f in FU["filas"] if f["h"] > 0]
    comun = pd.DataFrame([{
        "Estrato": f["n"], "Desde (m)": f["desde"], "Hasta (m)": f["hasta"], "h en fuste (m)": f["h"],
        "σ'v desde (kPa)": f["sv_desde"], "σ'v hasta (kPa)": f["sv_hasta"], "σ'v promedio (kPa)": f["sv_prom"],
        "K0": f["K0"], "tanφa": f["tan_a"]} for f in filas])
    st.markdown("**Tramo de cada estrato dentro de Lf y esfuerzos**")
    st.dataframe(comun.style.format(precision=3), hide_index=True)
    st.caption("σ'v promedio: si el NF corta el tramo, se promedian por separado la parte seca y la saturada.")

    ver = st.radio("Ver el detalle del método", C.METODOS_FUSTE, index=C.METODOS_FUSTE.index(metodo_fuste),
                   horizontal=True)
    det = []
    for f in filas:
        base = {"Estrato": f["n"], "h (m)": f["h"], "σ'v prom (kPa)": f["sv_prom"]}
        if ver == "Pág. 117":
            base.update({"ks = (ks/K0)·K0": f["ks"], "ca (kPa)": f["ca"], "tanφa": f["tan_a"]})
        elif ver == "α":
            base.update({"su = c (kPa)": f["su"], "α": f["alfa"]})
            base.pop("σ'v prom (kPa)")
        elif ver == "β":
            base.update({"K0": f["K0"], "tanφa": f["tan_a"], "β = K0·tanφa": f["beta"]})
        elif ver == "λ":
            base.update({"λ": FU["lam"], "su = c (kPa)": f["su"]})
        else:
            base.update({"ρ": f["rho"], "η (rad)": f["eta"], "Nq (Janbu)": f["Nq"], "Nc (Janbu)": f["Nc"],
                         "q0 (kPa)": f["q0"]})
        base.update({"fs (kPa)": f["fs"][ver], "Qs = fs·C·h (kN)": f["Qs"][ver]})
        det.append(base)
    ecu = {"Pág. 117": "fs = ca + ks·σ'v·tanφa", "α": "fs = α·su   (NSR-98 H.4-20)",
           "β": "fs = β·qv,  β = K0·tanφa   (NSR-98 H.4-21/22)",
           "λ": f"fs = λ·(qv + 2su),  λ = {FU['lam']:.3f} para L = {L:g} m   (NSR-98 H.4-23)",
           "ρ": "fs = ρ·q0,  ρ = coef·10^(−1.3·tanφ),  q0 = c·Nc + σ'v·Nq (Janbu)   (NSR-98 H.4-24/25)"}
    st.markdown(f"**{ver}:** `{ecu[ver]}`")
    st.dataframe(pd.DataFrame(det).style.format(precision=4 if ver == "ρ" else 3), hide_index=True)
    st.markdown(f"**Qs total ({ver}) = {FU['Qs'][ver]:,.2f} kN**")

    st.markdown("**Qs de todos los métodos**")
    st.dataframe(pd.DataFrame([{"Método": m, "Qs (kN)": FU["Qs"][m]} for m in C.METODOS_FUSTE])
                 .style.format({"Qs (kN)": "{:,.2f}"}), hide_index=True)

# ---------------------------------------------------------------- PUNTA
with t_pu:
    a, b, c_, d_, e_ = st.columns(5)
    a.metric("Estrato de la punta", PU["estrato"])
    b.metric("φ en la punta", f"{PU['phi']:.1f}°")
    c_.metric("c en la punta", f"{PU['c']:.1f} kPa")
    d_.metric("γ en la punta", f"{PU['gamma']:.2f} kN/m³", help="γ' = γsat − γw si la punta está bajo el NF")
    e_.metric("σ'v en la punta", f"{PU['sv']:.2f} kPa")
    st.caption(f"Ks = K0 = (1 − senφ)·√OCR = {PU['Ks']:.3f} (Meyerhof simplificado) · "
               f"η en la punta = {PU['eta']:.3f} rad (NSR-98 H.4-6, Janbu)")
    tp = pd.DataFrame([{"Método": m, "Nc": v["Nc"], "Nq": v["Nq"], "Nγ": v["Ng"], "qp (kPa)": v["qp"],
                        "Qp = qp·Ap (kN)": v["Qp"], "Ecuación": v["ecuacion"]}
                       for m, v in PU["metodos"].items()])
    st.dataframe(tp.style.format({"Nc": "{:,.2f}", "Nq": "{:,.2f}", "Nγ": "{:,.2f}", "qp (kPa)": "{:,.1f}",
                                  "Qp = qp·Ap (kN)": "{:,.1f}"}, na_rep="—"), hide_index=True)
    st.caption("Terzaghi: tabla de la diapositiva (base circular). Meyerhof: gráficas de cimentación profunda "
               "(β = +90°). Meyerhof simplificado: Meyerhof 1953, curva de pilote hincado o excavado. "
               "NSR-98 H.4-6 con Nq y Nc de Janbu.")

# ---------------------------------------------------------------- CARGA ADMISIBLE
with t_adm:
    pasos = pd.DataFrame([
        ("Qs (" + metodo_fuste + ")", R["Qs"], "kN"),
        ("Qp (" + metodo_punta + ")", R["Qp"], "kN"),
        ("Qu = Qp + Qs", ADM["Qu"], "kN"),
        (f"Qp / FSp  (FSp = {FSp:g})", ADM["Qp_FS"], "kN"),
        (f"Qs / FSs  (FSs = {FSs:g})", ADM["Qs_FS"], "kN"),
        ("Qadm parcial = Qp/FSp + Qs/FSs", ADM["parcial"], "kN"),
        ("FS global = Qu / Qadm parcial", ADM["FSg"], "—"),
        ("Qadm", ADM["Qadm"], "kN"),
    ], columns=["Paso", "Valor", "Unidad"])
    st.dataframe(pasos.style.format({"Valor": "{:,.2f}"}), hide_index=True)
    if ADM["usa_min"]:
        st.warning(f"FS global = {ADM['FSg']:.2f} < {FSmin:g} → **Qadm = Qu / {FSmin:g} = {ADM['Qadm']:,.1f} kN**")
    else:
        st.success(f"FS global = {ADM['FSg']:.2f} ≥ {FSmin:g} → **Qadm = Qp/FSp + Qs/FSs = {ADM['Qadm']:,.1f} kN**")

    def matriz(dic):
        return pd.DataFrame(dic).T.reindex(index=C.METODOS_PUNTA, columns=C.METODOS_FUSTE)

    def resaltar(df):
        est = pd.DataFrame("", index=df.index, columns=df.columns)
        est.loc[metodo_punta, metodo_fuste] = "background-color: #e2efda; font-weight: bold"
        return est

    st.markdown("**Comparación: Qu = Qp + Qs (kN)** — filas: punta, columnas: fuste")
    mq = matriz(R["matriz_Qu"])
    st.dataframe(mq.style.format("{:,.1f}").apply(resaltar, axis=None))
    st.markdown("**Comparación: Qadm (kN)** con la regla del FS global mínimo")
    ma = matriz(R["matriz_Qadm"])
    st.dataframe(ma.style.format("{:,.1f}").apply(resaltar, axis=None))
    st.caption("La celda resaltada es la combinación seleccionada en la barra lateral.")

# ---------------------------------------------------------------- ASENTAMIENTO
with t_ase:
    st.markdown("**Poulos y Davis — pilote por punta predominantemente:** "
                "δ = P·I / (Es·d),  I = I0 · RK · Rb · Rν")
    a, b = st.columns([1, 1])
    with a:
        tr = pd.DataFrame([{"Estrato": t["n"], "h dentro de L (m)": t["h"], "E (kPa)": t["E"], "ν": t["nu"],
                            "E·h": t["E"] * t["h"], "ν·h": t["nu"] * t["h"]} for t in ASE["tramos"] if t["h"] > 0])
        st.markdown("**Suelo a lo largo del pilote**")
        st.dataframe(tr.style.format({"h dentro de L (m)": "{:.2f}", "E (kPa)": "{:,.0f}", "ν": "{:.2f}",
                                      "E·h": "{:,.0f}", "ν·h": "{:.3f}"}), hide_index=True)
        st.caption("Es y νs se promedian ponderando por el espesor de cada estrato dentro de L.")
    with b:
        prm = pd.DataFrame([
            ("P (kN)", ASE["P"]), ("Es = Σ(E·h)/L (kPa)", ASE["Es"]), ("νs = Σ(ν·h)/L", ASE["nus"]),
            ("Eb = E del estrato de la punta (kPa)", ASE["Eb"]), ("Eb / Es", ASE["EbEs"]),
            ("L / d", ASE["LD"]), ("RA = Ap/(π·d²/4)", ASE["RA"]), ("K = Ep·RA / Es", ASE["K"]),
        ], columns=["Parámetro", "Valor"])
        st.markdown("**Parámetros**")
        st.dataframe(prm.style.format({"Valor": "{:,.3f}"}), hide_index=True)

    st.markdown("**Factores de las gráficas**")
    st.caption("«Valor de la gráfica» se interpola en las gráficas digitalizadas de las diapositivas. "
               "Si usted lee el valor a mano, escríbalo en «Valor manual» (0 = usar el de la gráfica).")
    info = {"I0": ("Fig. 5.18 (pág. 162)", "L/d"), "RK": ("Fig. 5.19 (pág. 163)", "L/d y K"),
            "Rb": ("Rb (págs. 167–168)", "L/d, K y Eb/Es"), "Rν": ("Fig. 5.21 (pág. 165)", "νs y K")}
    h1, h2, h3, h4, h5, h6 = st.columns([0.6, 1.4, 1.2, 1.1, 1.3, 1.0])
    for col, t in zip((h1, h2, h3, h4, h5, h6),
                      ("Factor", "Gráfica", "Se entra con", "Valor de la gráfica", "Valor manual", "Valor usado")):
        col.markdown(f"**{t}**")
    for k, (fig, entra) in info.items():
        c1_, c2_, c3_, c4_, c5_, c6_ = st.columns([0.6, 1.4, 1.2, 1.1, 1.3, 1.0])
        c1_.markdown(f"**{k}**")
        c2_.write(fig)
        c3_.write(entra)
        c4_.write(f"{ASE['grafica'][k]:.4f}")
        c5_.number_input(f"Manual {k}", min_value=0.0, max_value=10.0, value=0.0, step=0.001, format="%.4f",
                         key=f"man_{k}", label_visibility="collapsed")
        c6_.markdown(f"**{ASE['usado'][k]:.4f}**")
    st.caption("Rangos de las gráficas: I0 para L/d 2.5–100; RK para K 10–10 000; Rb para L/d 5–75, "
               "K 100–20 000 y Eb/Es 1–1000; Rν para K 100–2000. Fuera de rango se toma el borde.")
    r1, r2, r3 = st.columns(3)
    r1.metric("I = I0·RK·Rb·Rν", f"{ASE['I']:.4f}")
    r2.metric("δ = P·I/(Es·d)", f"{ASE['delta_m']:.5f} m")
    r3.metric("Asentamiento δ", f"{ASE['delta_mm']:.2f} mm")


# ---------------------------------------------------------------- GRÁFICAS
def barras(df, x, y, titulo, color=AZUL, orden=None):
    base = alt.Chart(df).encode(
        x=alt.X(f"{x}:N", sort=orden, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{y}:Q", title=y))
    b = base.mark_bar(color=color, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        tooltip=[x, alt.Tooltip(f"{y}:Q", format=",.1f")])
    t = base.mark_text(dy=-6, fontSize=12).encode(text=alt.Text(f"{y}:Q", format=",.1f"))
    return (b + t).properties(title=titulo, height=300)


def agrupadas(df, grupo, serie, y, titulo):
    return alt.Chart(df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X(f"{grupo}:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset(f"{serie}:N", sort=C.METODOS_FUSTE),
        y=alt.Y(f"{y}:Q", title=y),
        color=alt.Color(f"{serie}:N", sort=C.METODOS_FUSTE,
                        scale=alt.Scale(domain=C.METODOS_FUSTE, range=PALETA),
                        legend=alt.Legend(orient="bottom", title="Método de fuste")),
        tooltip=[grupo, serie, alt.Tooltip(f"{y}:Q", format=",.1f")],
    ).properties(title=titulo, height=320)


with t_gr:
    g1, g2 = st.columns(2)
    dq = pd.DataFrame({"Método": C.METODOS_FUSTE, "Qs (kN)": [FU["Qs"][m] for m in C.METODOS_FUSTE]})
    g1.altair_chart(barras(dq, "Método", "Qs (kN)", "Capacidad por fuste, Qs", orden=C.METODOS_FUSTE))
    dp = pd.DataFrame({"Método": C.METODOS_PUNTA, "Qp (kN)": [PU["metodos"][m]["Qp"] for m in C.METODOS_PUNTA]})
    g2.altair_chart(barras(dp, "Método", "Qp (kN)", "Capacidad por punta, Qp", orden=C.METODOS_PUNTA))
    g3, g4 = st.columns(2)
    da = pd.DataFrame([{"Punta": pm, "Fuste": fm, "Qadm (kN)": R["matriz_Qadm"][pm][fm]}
                       for pm in C.METODOS_PUNTA for fm in C.METODOS_FUSTE])
    g3.altair_chart(agrupadas(da, "Punta", "Fuste", "Qadm (kN)", "Qadm por combinación (punta + fuste)"))
    de = pd.DataFrame([{"Estrato": f"Estrato {f['n']}", "Fuste": m, "Qs (kN)": f["Qs"][m]}
                       for f in FU["filas"] if f["h"] > 0 for m in C.METODOS_FUSTE])
    g4.altair_chart(agrupadas(de, "Estrato", "Fuste", "Qs (kN)", "Aporte de fricción por estrato"))
    st.caption("Meyerhof da valores de punta mucho mayores porque Npq de sus gráficas es muy alto en arenas densas.")

# ---------------------------------------------------------------- ECUACIONES
with t_ec:
    st.markdown("#### Fuste (solo hasta Lf = mín(L, 15D))")
    st.latex(r"Q_s=\sum f_s\,C\,h \qquad C=\pi D")
    st.latex(r"\text{Pág. 117: } f_s=c_a+k_s\,\sigma'_v\tan\phi_a \qquad k_s=(k_s/K_0)\,K_0"
             r"\qquad K_0=(1-\sin\phi)\sqrt{OCR}")
    st.latex(r"\alpha:\ f_s=\alpha\,s_u \qquad \alpha=\begin{cases}1 & s_u\le 25\\ 1-\dfrac{s_u-25}{90} & 25<s_u<70\\"
             r" 0.5 & s_u\ge 70\end{cases}")
    st.latex(r"\beta:\ f_s=\beta\,q_v \qquad \beta=K_0\tan\phi_a")
    st.latex(r"\lambda:\ f_s=\lambda\,(q_v+2s_u)\qquad \lambda\ \text{de la Figura H.4-5 según } L")
    st.latex(r"\rho:\ f_s=\rho\,q_0 \qquad \rho=C_\rho\,10^{-1.3\tan\phi} \qquad q_0=c\,N_c+\sigma'_v\,N_q")
    st.latex(r"\text{Janbu: } N_q=\left(\tan\phi+\sqrt{1+\tan^2\phi}\right)^2 e^{2\eta\tan\phi}"
             r"\qquad N_c=(N_q-1)\cot\phi \qquad \eta=\pi/3\ \text{(suelta)},\ 0.58\pi\ \text{(densa)}")
    st.markdown("#### Punta (en z = L)")
    st.latex(r"\text{Terzaghi: } q_p=1.2\,c\,N_c+\sigma'_v N_q+0.6\,\gamma\,\tfrac{B}{2}\,N_\gamma")
    st.latex(r"\text{Meyerhof: } q_p=c\,N_{pc}+\sigma_o N_{pq}+\gamma\,\tfrac{B}{2}\,N_{p\gamma}")
    st.latex(r"\text{Meyerhof simplificado: } q_p=c\,N_c+K_s\,\sigma'_v\,N_q \qquad K_s=K_0")
    st.latex(r"\text{NSR-98 H.4-6: } q_o=c\,N_c+q_{vo}\,N_q\ \ \text{(Janbu)} \qquad Q_p=q_p\,A_p")
    st.markdown("#### Carga admisible")
    st.latex(r"Q_{adm}=\frac{Q_p}{FS_p}+\frac{Q_s}{FS_s}\qquad \text{si } \frac{Q_u}{Q_{adm}}<FS_{min}"
             r"\Rightarrow Q_{adm}=\frac{Q_u}{FS_{min}}")
    st.markdown("#### Asentamiento (Poulos y Davis, pilote por punta)")
    st.latex(r"\delta=\frac{P\,I}{E_s\,d}\qquad I=I_0\,R_K\,R_b\,R_\nu \qquad K=\frac{E_p R_A}{E_s}"
             r"\qquad E_s=\frac{\sum E_i h_i}{L}")


# =============================================================================
# DESCARGA DE RESULTADOS
# =============================================================================
def excel_resultados():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame([("D (m)", D), ("L (m)", L), ("Tipo", tipo), ("NF (m)", NF), ("γw", gw),
                      ("Método de fuste", metodo_fuste), ("Método de punta", metodo_punta),
                      ("FSp", FSp), ("FSs", FSs), ("FS mínimo", FSmin), ("Ep (kPa)", Ep)],
                     columns=["Dato", "Valor"]).to_excel(xw, sheet_name="Datos", index=False)
        editado.to_excel(xw, sheet_name="Estratigrafía", index=False)
        comun.to_excel(xw, sheet_name="Fuste", index=False)
        pd.DataFrame([{"Estrato": f["n"], **{f"fs {m} (kPa)": f["fs"][m] for m in C.METODOS_FUSTE},
                       **{f"Qs {m} (kN)": f["Qs"][m] for m in C.METODOS_FUSTE}} for f in filas]
                     ).to_excel(xw, sheet_name="Fuste", index=False, startrow=len(comun) + 3)
        tp.to_excel(xw, sheet_name="Punta", index=False)
        pasos.to_excel(xw, sheet_name="Carga admisible", index=False)
        mq.to_excel(xw, sheet_name="Carga admisible", startrow=len(pasos) + 3)
        ma.to_excel(xw, sheet_name="Carga admisible", startrow=len(pasos) + 10)
        pd.DataFrame([("P (kN)", ASE["P"]), ("Es (kPa)", ASE["Es"]), ("νs", ASE["nus"]), ("Eb (kPa)", ASE["Eb"]),
                      ("L/d", ASE["LD"]), ("K", ASE["K"]), ("Eb/Es", ASE["EbEs"]),
                      *[(f"{k} (usado)", v) for k, v in ASE["usado"].items()],
                      ("I", ASE["I"]), ("δ (mm)", ASE["delta_mm"])],
                     columns=["Parámetro", "Valor"]).to_excel(xw, sheet_name="Asentamiento", index=False)
    return buf.getvalue()


st.divider()
st.download_button("Descargar resultados en Excel", data=excel_resultados(),
                   file_name="resultados_pilote.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
