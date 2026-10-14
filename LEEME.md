# Aplicación: capacidad portante y asentamiento de un pilote en arena

Aplicación en Python (Streamlit). Usa los mismos métodos y criterios del Excel
`Capacidad_Portante_Pilote_v6.xlsx`, y con los mismos datos da los mismos resultados.

## Archivos

| Archivo | Qué contiene |
|---|---|
| `app.py` | La interfaz: formularios, tablas, gráficas y descarga de resultados |
| `calculos.py` | El motor de cálculo: fuste, punta, carga admisible y asentamiento |
| `tablas.py` | Las tablas digitalizadas de las diapositivas (Terzaghi, Meyerhof, λ, Poulos y Davis) |
| `requirements.txt` | Librerías necesarias |

## Cómo ejecutarla

1. Instale Python 3.10 o superior.
2. Abra una terminal en esta carpeta e instale las librerías:
   ```
   pip install -r requirements.txt
   ```
3. Ejecute:
   ```
   streamlit run app.py
   ```
   La aplicación se abre sola en el navegador (normalmente en http://localhost:8501).

## Cómo usarla

1. **Barra lateral:** datos del pilote (D, L, tipo), nivel freático, métodos de fuste y punta,
   factores de seguridad y datos del asentamiento (Ep y la carga P).
   En «Coeficientes de los métodos» están ca/c, ks/K0, tanφa/tanφ, el coeficiente de ρ y la falla de Terzaghi.
2. **Estratigrafía:** edite la tabla directamente. Con el **+** de la última fila agrega estratos.
   La compacidad (Suelta/Densa) define η de Janbu; escriba «η manual» solo si quiere otro valor.
3. **Resultados:** arriba se ven Qs, Qp, Qu, Qadm y el asentamiento. Las pestañas muestran el detalle:
   - **Fuste:** tabla por estrato hasta Lf = mín(L, 15D) y el detalle de cada método.
   - **Punta:** los 4 métodos con sus factores.
   - **Carga admisible:** Qp/FSp + Qs/FSs, verificación del FS global mínimo y matrices comparativas.
   - **Asentamiento:** Poulos y Davis para pilote por punta (I = I0·RK·Rb·Rν). Puede escribir valores
     leídos a mano de las gráficas en «Valor manual».
   - **Gráficas** y **Ecuaciones**.
4. **Descargar resultados en Excel:** botón al final de la página.

El botón «Cargar el ejemplo del Excel» de la barra lateral restaura los datos del ejemplo.
