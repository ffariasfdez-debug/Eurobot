

import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURACION
# ============================================================================
DB_FILE = 'eurobot_datos.json'
CAPITAL_TOTAL = 30000
MAX_POSICIONES = 10
MAX_POR_COMPRA = 2000
MAX_COMPRAS_SEMANA = 2

CALADEROS = {
    "DAX": "^GDAXI",
    "EUROSTOXX50": "^STOXX50E",
    "IBEX35": "^IBEX"
}

# ============================================================================
# PERSISTENCIA
# ============================================================================
def cargar_datos():
    if not os.path.exists(DB_FILE):
        return {
            "capital_disponible": CAPITAL_TOTAL,
            "posiciones": {},  # {ticker: {"precio": x, "cantidad": y, "fecha": z, "invertido": w}}
            "historial": [],
            "compras_semana": {},  # {"2024-W23": 2}
            "ultima_ejecucion": None
        }
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            "capital_disponible": CAPITAL_TOTAL,
            "posiciones": {},
            "historial": [],
            "compras_semana": {},
            "ultima_ejecucion": None
        }

def guardar_datos(datos):
    datos["ultima_ejecucion"] = datetime.now().strftime('%d/%m/%Y %H:%M')
    with open(DB_FILE, 'w') as f:
        json.dump(datos, f, indent=2)

# ============================================================================
# FUNCIONES DE MERCADO
# ============================================================================
def get_semana_actual():
    return datetime.now().strftime("%Y-W%U")

def compras_esta_semana(datos):
    semana = get_semana_actual()
    return datos["compras_semana"].get(semana, 0)

def puede_comprar(datos):
    semana = get_semana_actual()
    compras = datos["compras_semana"].get(semana, 0)
    if compras >= MAX_COMPRAS_SEMANA:
        return False, f"Límite semanal alcanzado: {compras}/{MAX_COMPRAS_SEMANA}"
    if len(datos["posiciones"]) >= MAX_POSICIONES:
        return False, f"Cartera llena: {len(datos['posiciones'])}/{MAX_POSICIONES}"
    if datos["capital_disponible"] < MAX_POR_COMPRA:
        return False, f"Capital insuficiente: {datos['capital_disponible']:.0f}€"
    return True, "OK"

def registrar_compra(datos, ticker, precio, cantidad, invertido):
    semana = get_semana_actual()
    datos["compras_semana"][semana] = datos["compras_semana"].get(semana, 0) + 1
    datos["posiciones"][ticker] = {
        "precio": round(precio, 2),
        "cantidad": round(cantidad, 4),
        "fecha": datetime.now().strftime('%d/%m/%Y'),
        "invertido": round(invertido, 2),
        "mercado": [k for k, v in CALADEROS.items() if v == ticker][0]
    }
    datos["capital_disponible"] -= invertido
    datos["historial"].append(f"✅ COMPRA: {ticker} @ {precio:.2f}€ | {cantidad:.4f} uds | {invertido:.0f}€ | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    guardar_datos(datos)

def registrar_venta(datos, ticker, precio_actual, motivo="Tendencia rota"):
    if ticker in datos["posiciones"]:
        pos = datos["posiciones"][ticker]
        valor_actual = pos["cantidad"] * precio_actual
        pnl = valor_actual - pos["invertido"]
        pnl_pct = (pnl / pos["invertido"]) * 100 if pos["invertido"] > 0 else 0

        datos["capital_disponible"] += valor_actual
        del datos["posiciones"][ticker]

        emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⬜"
        datos["historial"].append(
            f"{emoji} VENTA: {ticker} @ {precio_actual:.2f}€ | P&L: {pnl:+.2f}€ ({pnl_pct:+.1f}%) | {motivo} | {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        guardar_datos(datos)
        return True, pnl
    return False, 0

# ============================================================================
# ANALISIS TECNICO
# ============================================================================
def analizar_tendencia(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df.empty or len(df) < 50:
            return None, "Sin datos"

        # Manejar MultiIndex de yfinance
        if isinstance(df.columns, pd.MultiIndex):
            close_col = ('Close', ticker)
            if close_col not in df.columns:
                close_col = 'Close'
        else:
            close_col = 'Close'

        precios = df[close_col].squeeze()
        if isinstance(precios, pd.DataFrame):
            precios = precios.iloc[:, 0]

        sma10 = precios.rolling(window=10).mean().iloc[-1]
        sma50 = precios.rolling(window=50).mean().iloc[-1]
        precio_actual = precios.iloc[-1]

        # Calcular RSI
        delta = precios.diff()
        ganancia = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perdida = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganancia / perdida
        rsi = 100 - (100 / (1 + rs))
        rsi_valor = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

        sma10_val = float(sma10.item() if hasattr(sma10, 'item') else sma10)
        sma50_val = float(sma50.item() if hasattr(sma50, 'item') else sma50)
        precio_val = float(precio_actual.item() if hasattr(precio_actual, 'item') else precio_actual)

        tendencia_alcista = sma10_val > sma50_val
        fuerza = "FUERTE" if precio_val > sma10_val else "DEBIL"

        return {
            "precio": round(precio_val, 2),
            "sma10": round(sma10_val, 2),
            "sma50": round(sma50_val, 2),
            "tendencia": tendencia_alcista,
            "fuerza": fuerza,
            "rsi": round(rsi_valor, 1),
            "nombre": [k for k, v in CALADEROS.items() if v == ticker][0]
        }, "OK"
    except Exception as e:
        return None, str(e)

def calcular_score_eurobot(analisis):
    score = 0
    motivos = []

    if analisis["tendencia"]:
        score += 5
        motivos.append("Tendencia alcista SMA10>SMA50 (+5)")

    if analisis["fuerza"] == "FUERTE":
        score += 3
        motivos.append("Precio > SMA10 (+3)")
    else:
        motivos.append("Precio < SMA10 (0)")

    if 30 < analisis["rsi"] < 70:
        score += 2
        motivos.append(f"RSI {analisis['rsi']:.0f} en zona neutral (+2)")
    elif analisis["rsi"] < 30:
        score += 1
        motivos.append(f"RSI {analisis['rsi']:.0f} sobreventa (+1)")
    else:
        motivos.append(f"RSI {analisis['rsi']:.0f} sobrecompra (0)")

    return score, motivos

# ============================================================================
# LOGICA AUTONOMA
# ============================================================================
def ejecutar_logica_autonoma(datos):
    acciones = []

    # 1. Analizar todos los caladeros
    analisis_mercado = {}
    for nombre, ticker in CALADEROS.items():
        analisis, error = analizar_tendencia(ticker)
        if analisis:
            analisis_mercado[ticker] = analisis
        else:
            acciones.append(f"⚠️ {nombre}: Error - {error}")

    if not analisis_mercado:
        return acciones + ["❌ No se pudo analizar ningún mercado"]

    # 2. VENDER posiciones que ya no son alcistas
    for ticker in list(datos["posiciones"].keys()):
        if ticker in analisis_mercado:
            if not analisis_mercado[ticker]["tendencia"]:
                ok, pnl = registrar_venta(datos, ticker, analisis_mercado[ticker]["precio"], "Tendencia rota")
                if ok:
                    acciones.append(f"🗑️ VENDIDO {ticker}: Tendencia rota | P&L: {pnl:+.2f}€")

    # 3. Calcular scores y ordenar
    scores = {}
    for ticker, analisis in analisis_mercado.items():
        score, motivos = calcular_score_eurobot(analisis)
        scores[ticker] = {"score": score, "motivos": motivos, "analisis": analisis}

    # Ordenar por score descendente
    tickers_ordenados = sorted(scores.keys(), key=lambda x: scores[x]["score"], reverse=True)

    # 4. COMPRAR las mejores oportunidades
    for ticker in tickers_ordenados:
        if ticker in datos["posiciones"]:
            continue  # Ya tenemos esta posición

        if not scores[ticker]["analisis"]["tendencia"]:
            continue  # No es alcista

        if scores[ticker]["score"] < 5:
            continue  # Score insuficiente

        puede, msg = puede_comprar(datos)
        if not puede:
            acciones.append(f"⏳ {ticker}: {msg}")
            continue

        precio = scores[ticker]["analisis"]["precio"]
        cantidad = MAX_POR_COMPRA / precio
        invertido = MAX_POR_COMPRA

        registrar_compra(datos, ticker, precio, cantidad, invertido)
        acciones.append(f"💰 COMPRADO {ticker}: Score {scores[ticker]['score']}/10 | {invertido:.0f}€ @ {precio:.2f}€")

    return acciones

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="🇪🇺 Eurobot Autónomo", layout="wide")

st.title("🇪🇺 Eurobot Autónomo")
st.write(f"**Capital:** {CAPITAL_TOTAL:,.0f}€ | **Máx:** {MAX_POSICIONES} pos | **Compra:** {MAX_POR_COMPRA:,.0f}€ | **Semana:** {MAX_COMPRAS_SEMANA} compras")
st.write(f"**Caladeros:** DAX, EuroStoxx 50, IBEX 35")
st.write("---")

# Cargar datos
datos = cargar_datos()

# Ejecutar lógica autónoma
with st.spinner("🤖 Eurobot analizando mercados..."):
    acciones = ejecutar_logica_autonoma(datos)

# Recargar datos después de la ejecución
datos = cargar_datos()

# Mostrar acciones del bot
if acciones:
    st.write("### 📝 Acciones Autónomas del Bot")
    for accion in acciones:
        st.write(accion)
    st.write("---")

# METRICAS PRINCIPALES
col1, col2, col3, col4, col5 = st.columns(5)
invertido = sum(p["invertido"] for p in datos["posiciones"].values())
capital_disponible = datos["capital_disponible"]

pnl_total = 0
for ticker, pos in datos["posiciones"].items():
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False)
        if not df.empty:
            close_col = 'Close'
            if isinstance(df.columns, pd.MultiIndex):
                close_col = ('Close', ticker) if ('Close', ticker) in df.columns else 'Close'
            precio_actual = float(df[close_col].iloc[-1].item() if hasattr(df[close_col].iloc[-1], 'item') else df[close_col].iloc[-1])
            valor_actual = pos["cantidad"] * precio_actual
            pnl_total += valor_actual - pos["invertido"]
    except:
        pass

col1.metric("Capital Total", f"{CAPITAL_TOTAL:,.0f}€")
col2.metric("Invertido", f"{invertido:,.0f}€")
col3.metric("Disponible", f"{capital_disponible:,.0f}€")
col4.metric("P&L Total", f"{pnl_total:+.2f}€", delta=f"{pnl_total/CAPITAL_TOTAL*100:+.1f}%")
col5.metric("Posiciones", f"{len(datos['posiciones'])}/{MAX_POSICIONES}")

# ESTADO DE LOS CALADEROS
st.write("### 📊 Estado de los Caladeros")
for nombre, ticker in CALADEROS.items():
    analisis, error = analizar_tendencia(ticker)
    if analisis:
        col_info, col_precio, col_tendencia, col_score = st.columns([2, 1, 2, 1])
        with col_info:
            st.write(f"**{nombre}** ({ticker})")
        with col_precio:
            st.write(f"{analisis['precio']:.2f}€")
        with col_tendencia:
            if analisis["tendencia"]:
                st.success(f"🟢 Alcista | SMA10: {analisis['sma10']:.0f} | SMA50: {analisis['sma50']:.0f}")
            else:
                st.error(f"🔴 Bajista | SMA10: {analisis['sma10']:.0f} | SMA50: {analisis['sma50']:.0f}")
        with col_score:
            score, _ = calcular_score_eurobot(analisis)
            st.write(f"Score: {score}/10")
    else:
        st.error(f"❌ {nombre}: {error}")

# CARTERA ACTUAL
st.write("---")
st.write(f"### 📈 Cartera ({len(datos['posiciones'])}/{MAX_POSICIONES} posiciones)")

if datos["posiciones"]:
    cartera_data = []
    for ticker, pos in datos["posiciones"].items():
        try:
            # Descargar datos para calcular rentabilidad del día
            df_hoy = yf.download(ticker, period="2d", interval="1d", progress=False)
            df_1min = yf.download(ticker, period="1d", interval="1m", progress=False)

            def get_scalar(val):
                if hasattr(val, 'item'):
                    return float(val.item())
                elif isinstance(val, pd.Series):
                    return float(val.iloc[0])
                return float(val)

            if not df_hoy.empty and len(df_hoy) >= 2:
                close_col = 'Close'
                open_col = 'Open'
                if isinstance(df_hoy.columns, pd.MultiIndex):
                    close_col = ('Close', ticker) if ('Close', ticker) in df_hoy.columns else 'Close'
                    open_col = ('Open', ticker) if ('Open', ticker) in df_hoy.columns else 'Open'

                precio_cierre_ayer = get_scalar(df_hoy[close_col].iloc[-2])
                precio_apertura_hoy = get_scalar(df_hoy[open_col].iloc[-1])
                precio_actual = get_scalar(df_hoy[close_col].iloc[-1])

                # Si tenemos datos intradía más recientes, usarlos
                if not df_1min.empty:
                    close_col_1m = 'Close'
                    if isinstance(df_1min.columns, pd.MultiIndex):
                        close_col_1m = ('Close', ticker) if ('Close', ticker) in df_1min.columns else 'Close'
                    precio_actual = get_scalar(df_1min[close_col_1m].iloc[-1])
            else:
                precio_cierre_ayer = pos["precio"]
                precio_apertura_hoy = pos["precio"]
                precio_actual = pos["precio"]

            # Rentabilidad del día (desde apertura)
            rend_dia_pct = ((precio_actual - precio_apertura_hoy) / precio_apertura_hoy) * 100 if precio_apertura_hoy > 0 else 0
            rend_dia_eur = pos["cantidad"] * (precio_actual - precio_apertura_hoy)

            # Rentabilidad acumulada (desde compra)
            rend_acum_pct = ((precio_actual - pos["precio"]) / pos["precio"]) * 100 if pos["precio"] > 0 else 0
            rend_acum_eur = pos["cantidad"] * (precio_actual - pos["precio"])

            # Stop Loss y Take Profit (basado en ATR o volatilidad)
            try:
                df_atr = yf.download(ticker, period="1mo", interval="1d", progress=False)
                if not df_atr.empty and len(df_atr) >= 14:
                    close_col = 'Close'
                    high_col = 'High'
                    low_col = 'Low'
                    if isinstance(df_atr.columns, pd.MultiIndex):
                        close_col = ('Close', ticker) if ('Close', ticker) in df_atr.columns else 'Close'
                        high_col = ('High', ticker) if ('High', ticker) in df_atr.columns else 'High'
                        low_col = ('Low', ticker) if ('Low', ticker) in df_atr.columns else 'Low'

                    high_low = df_atr[high_col].squeeze() - df_atr[low_col].squeeze()
                    high_close = abs(df_atr[high_col].squeeze() - df_atr[close_col].shift().squeeze())
                    low_close = abs(df_atr[low_col].squeeze() - df_atr[close_col].shift().squeeze())
                    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                    atr_val = float(tr.rolling(window=14).mean().iloc[-1])

                    stop_loss = pos["precio"] - (atr_val * 2)  # 2x ATR debajo
                    take_profit = pos["precio"] + (atr_val * 3)  # 3x ATR arriba
                else:
                    stop_loss = pos["precio"] * 0.95  # -5%
                    take_profit = pos["precio"] * 1.15  # +15%
            except:
                stop_loss = pos["precio"] * 0.95
                take_profit = pos["precio"] * 1.15

            # Color según rentabilidad
            color_dia = "🟢" if rend_dia_pct >= 0 else "🔴"
            color_acum = "🟢" if rend_acum_pct >= 0 else "🔴"

            cartera_data.append({
                "Ticker": ticker,
                "Nombre": pos["mercado"],
                "Fecha Compra": pos["fecha"],
                "Precio Entrada": f"{pos['precio']:.2f}€",
                "Precio Actual": f"{precio_actual:.2f}€",
                "Cantidad": f"{pos['cantidad']:.4f}",
                "Invertido": f"{pos['invertido']:.0f}€",
                f"Rend. Día {color_dia}": f"{rend_dia_pct:+.2f}% ({rend_dia_eur:+.2f}€)",
                f"Rend. Acum. {color_acum}": f"{rend_acum_pct:+.2f}% ({rend_acum_eur:+.2f}€)",
                "Stop Loss": f"{stop_loss:.2f}€",
                "Take Profit": f"{take_profit:.2f}€",
                "Distancia SL": f"{((precio_actual - stop_loss) / precio_actual * 100):.1f}%",
                "Distancia TP": f"{((take_profit - precio_actual) / precio_actual * 100):.1f}%"
            })
        except Exception as e:
            st.warning(f"Error cargando {ticker}: {e}")
            cartera_data.append({
                "Ticker": ticker,
                "Nombre": pos["mercado"],
                "Fecha Compra": pos["fecha"],
                "Precio Entrada": f"{pos['precio']:.2f}€",
                "Precio Actual": "Error",
                "Cantidad": f"{pos['cantidad']:.4f}",
                "Invertido": f"{pos['invertido']:.0f}€",
                "Rend. Día": "N/A",
                "Rend. Acum.": "N/A",
                "Stop Loss": "N/A",
                "Take Profit": "N/A",
                "Distancia SL": "N/A",
                "Distancia TP": "N/A"
            })

    df_cartera = pd.DataFrame(cartera_data)
    st.dataframe(df_cartera, use_container_width=True)

    # Resumen de rentabilidades
    total_rend_dia = sum([float(row[f"Rend. Día {('🟢' if float(row[f'Rend. Día 🟢'].split('%')[0]) >= 0 else '🔴')}"].split('€')[0].split('(')[1]) 
                        for row in cartera_data if "€" in row.get(f"Rend. Día 🟢", "") or "€" in row.get(f"Rend. Día 🔴", "")])

    st.write("---")
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.metric("Rentabilidad Total Acumulada", f"{sum([float(row['Rend. Acum. 🟢'].split('%')[0]) if '🟢' in row.get('Rend. Acum. 🟢', '') else float(row['Rend. Acum. 🔴'].split('%')[0]) for row in cartera_data]):+.2f}%")
    with col_r2:
        st.metric("Mejor Posición", max([float(row['Rend. Acum. 🟢'].split('%')[0]) if '🟢' in row.get('Rend. Acum. 🟢', '') else float(row['Rend. Acum. 🔴'].split('%')[0]) for row in cartera_data]))
    with col_r3:
        st.metric("Peor Posición", min([float(row['Rend. Acum. 🟢'].split('%')[0]) if '🟢' in row.get('Rend. Acum. 🟢', '') else float(row['Rend. Acum. 🔴'].split('%')[0]) for row in cartera_data]))
else:
    st.info("Cartera vacía. El bot comprará cuando detecte tendencias alcistas.")
# HISTORIAL
st.write("---")
st.write("### 📜 Historial de Operaciones")
if datos["historial"]:
    for op in reversed(datos["historial"][-20:]):
        st.write(op)
else:
    st.info("Sin operaciones todavía.")

# CONTROLES MANUALES (para emergencias)
with st.expander("⚙️ Controles Manuales (Emergencia)"):
    col_reset, col_forzar = st.columns(2)
    with col_reset:
        if st.button("🗑️ Resetear Todo", type="secondary"):
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            st.success("✅ Datos reseteados. Recarga la página.")
            st.rerun()
    with col_forzar:
        if st.button("🔄 Forzar Ejecución", type="primary"):
            st.rerun()

st.write("---")
st.caption(f"🇪🇺 Eurobot Autónomo | Última ejecución: {datos.get('ultima_ejecucion', 'Nunca')} | Funciona aunque la app esté apagada (usa persistencia JSON)")
