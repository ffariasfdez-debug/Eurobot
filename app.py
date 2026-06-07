
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import time

# ============================================================================
# CONFIGURACION EUROBOT
# ============================================================================
DB_FILE = 'eurobot_cartera.json'
DB_BACKUP = 'eurobot_cartera.json.bak'
HISTORIAL_FILE = 'eurobot_historial.json'

CAPITAL_TOTAL = 30000.0
MAX_POR_ACCION = 2000.0
MAX_POSICIONES = 10
COMPRAS_SEMANALES_MAX = 2
STOP_LOSS_PCT = -8.0  # -8%

# Horario Europa: Lunes-Viernes 9:30-17:30 CET
HORA_APERTURA_CET = 9
HORA_CIERRE_CET = 17

# ============================================================================
# UNIVERSO DE ACCIONES EUROPEAS (solo EUR)
# ============================================================================
UNIVERSO_EUROPEO = {
    "🇪🇸 IBEX 35": [
        "ITX.MC", "SAN.MC", "BBVA.MC", "IBE.MC", "REP.MC",
        "TEF.MC", "AMS.MC", "AENA.MC", "CLNX.MC", "FER.MC",
        "GRF.MC", "IAG.MC", "MAP.MC", "MRL.MC", "NTGY.MC",
        "RED.MC", "SAB.MC", "SGRE.MC", "SLR.MC", "ACS.MC"
    ],
    "🇪🇺 EURO STOXX 50": [
        "ASML.AS", "SAP.DE", "MC.PA", "SIE.DE", "OR.PA",
        "SAN.PA", "AIR.PA", "SU.PA", "AI.PA", "BNP.PA",
        "DG.PA", "EL.PA", "ENEL.MI", "ENI.MI", "ISP.MI",
        "MBG.DE", "MUV2.DE", "RMS.PA", "SAF.PA", "SCHN.PA"
    ],
    "🇩🇪 DAX 40 (EUR)": [
        "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "ADS.DE",
        "AIR.DE", "BAS.DE", "BAYN.DE", "BEI.DE", "BMW.DE",
        "CBK.DE", "CON.DE", "1COV.DE", "DBK.DE", "DB1.DE",
        "DPW.DE", "DRI.DE", "EVK.DE", "FME.DE", "FRE.DE",
        "HEI.DE", "HEN3.DE", "IFX.DE", "LIN.DE", "MRK.DE",
        "MTX.DE", "MUV2.DE", "RWE.DE", "SAP.DE", "SRT3.DE",
        "SY1.DE", "VNA.DE", "VOW3.DE", "ZAL.DE"
    ]
}

# Eliminar duplicados y mantener orden
TODOS_TICKERS = []
for lista in UNIVERSO_EUROPEO.values():
    for t in lista:
        if t not in TODOS_TICKERS:
            TODOS_TICKERS.append(t)

# ============================================================================
# PERSISTENCIA (con backup .bak)
# ============================================================================
def _guardar_con_backup(data, filepath, backup_path):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f_orig:
                contenido = f_orig.read()
            with open(backup_path, 'w') as f_bak:
                f_bak.write(contenido)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error guardando {filepath}: {e}")
        return False

def cargar_cartera():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    if os.path.exists(DB_BACKUP):
        try:
            with open(DB_BACKUP, 'r') as f:
                data = json.load(f)
            st.success("✅ Cartera recuperada desde backup")
            return data
        except:
            pass
    return {
        "capital_total": CAPITAL_TOTAL,
        "capital_disponible": CAPITAL_TOTAL,
        "posiciones": {},
        "historial": [],
        "compras_esta_semana": 0,
        "semana_actual": datetime.now().strftime("%Y-W%U")
    }

def guardar_cartera(data):
    _guardar_con_backup(data, DB_FILE, DB_BACKUP)

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return []

def guardar_historial(historial):
    with open(HISTORIAL_FILE, 'w') as f:
        json.dump(historial, f, indent=2)

# ============================================================================
# FUNCIONES DE ANALISIS
# ============================================================================
def descargar_datos_batch(tickers, period="3mo"):
    """Descarga datos batch para todos los tickers."""
    try:
        datos = yf.download(" ".join(tickers), period=period, interval="1d", 
                           group_by="ticker", progress=False)
        return datos
    except:
        return pd.DataFrame()

def extraer_historial(datos_globales, ticker):
    """Extrae historial de un ticker específico del batch."""
    try:
        if not datos_globales.empty:
            if ticker in datos_globales.columns.get_level_values(0):
                h = datos_globales[ticker].dropna()
                if not h.empty:
                    return h
    except:
        pass
    try:
        return yf.Ticker(ticker).history(period="3mo", interval="1d")
    except:
        return pd.DataFrame()

def calcular_metricas(historial, precio_actual, ticker):
    """Calcula métricas para scoring."""
    if historial.empty or len(historial) < 50:
        return None

    try:
        # Tendencia: SMA10 vs SMA50
        sma10 = historial["Close"].iloc[-10:].mean()
        sma50 = historial["Close"].iloc[-50:].mean()
        tendencia_alcista = precio_actual > sma10 > sma50

        # Momentum 60d
        precio_60d = historial["Close"].iloc[-60] if len(historial) >= 60 else historial["Close"].iloc[0]
        if precio_60d > 0:
            momentum = ((precio_actual / precio_60d) ** (252/60) - 1) * 100
            momentum = round(momentum, 1)
            # Limitar momentum anómalo (>200% probablemente split/gap)
            if momentum > 200 or momentum < -80:
                precio_media_20d = historial["Close"].iloc[-20:].mean()
                if precio_media_20d > 0:
                    momentum = ((precio_actual / precio_media_20d) ** (252/20) - 1) * 100
                    momentum = round(momentum, 1)
        else:
            momentum = 0.0

        # Upside Analista
        upside = None
        try:
            info = yf.Ticker(ticker).info
            target = info.get("targetMedianPrice", None)
            if target and target > 0 and precio_actual > 0:
                upside = ((target - precio_actual) / precio_actual) * 100
                if -50 < upside < 100:
                    upside = round(upside, 1)
                else:
                    upside = None
        except:
            pass

        return {
            "tendencia_alcista": tendencia_alcista,
            "sma10": sma10,
            "sma50": sma50,
            "momentum": momentum,
            "upside": upside,
            "precio": precio_actual
        }
    except:
        return None

def calcular_score(metricas):
    """Scoring sobre 10 puntos."""
    if not metricas:
        return 0

    score = 0
    motivos = []

    # Tendencia (40% del peso)
    if metricas["tendencia_alcista"]:
        score += 4
        motivos.append("Tendencia alcista (+4)")
    else:
        motivos.append("Sin tendencia alcista")

    # Momentum 60d (30%)
    m = metricas["momentum"]
    if m >= 20:
        score += 3
        motivos.append(f"Momentum fuerte {m:.1f}% (+3)")
    elif m >= 10:
        score += 2
        motivos.append(f"Momentum moderado {m:.1f}% (+2)")
    elif m > 0:
        score += 1
        motivos.append(f"Momentum positivo {m:.1f}% (+1)")
    else:
        motivos.append(f"Momentum negativo {m:.1f}%")

    # Upside Analista (30%)
    u = metricas["upside"]
    if u is not None and u > 20:
        score += 3
        motivos.append(f"Upside fuerte {u:.1f}% (+3)")
    elif u is not None and u > 10:
        score += 2
        motivos.append(f"Upside moderado {u:.1f}% (+2)")
    elif u is not None and u > 0:
        score += 1
        motivos.append(f"Upside positivo {u:.1f}% (+1)")
    else:
        motivos.append("Sin upside confirmado")

    # Penalizacion: si no hay tendencia alcista, maximo 5
    if not metricas["tendencia_alcista"] and score > 5:
        score = 5
        motivos.append("Score limitado a 5 sin tendencia alcista")

    return max(0, score), motivos

# ============================================================================
# LOGICA DE COMPRA/VENTA
# ============================================================================
def puede_comprar_esta_semana(cartera):
    """Verifica si se pueden hacer compras esta semana."""
    semana_actual = datetime.now().strftime("%Y-W%U")
    if cartera.get("semana_actual") != semana_actual:
        cartera["semana_actual"] = semana_actual
        cartera["compras_esta_semana"] = 0
        return True, 0
    return cartera["compras_esta_semana"] < COMPRAS_SEMANALES_MAX, cartera["compras_esta_semana"]

def evaluar_posiciones(cartera, datos_activos):
    """Evalua posiciones actuales: stop-loss, tendencia rota, ranking."""
    alertas = []
    posiciones = cartera.get("posiciones", {})

    for ticker, pos in list(posiciones.items()):
        precio_entrada = pos["precio_entrada"]
        precio_actual = pos.get("precio_actual", precio_entrada)

        # 1. Stop-loss
        cambio_pct = ((precio_actual - precio_entrada) / precio_entrada) * 100
        if cambio_pct <= STOP_LOSS_PCT:
            alertas.append({
                "ticker": ticker,
                "tipo": "STOP_LOSS",
                "motivo": f"Caida {cambio_pct:.1f}% <= {STOP_LOSS_PCT}%",
                "precio_entrada": precio_entrada,
                "precio_actual": precio_actual,
                "auto_ejecutar": True
            })
            continue

        # 2. Tendencia rota
        info = datos_activos.get(ticker)
        if info and not info.get("tendencia_alcista", True):
            alertas.append({
                "ticker": ticker,
                "tipo": "TENDENCIA_ROTA",
                "motivo": "SMA10 < SMA50, tendencia invertida",
                "precio_entrada": precio_entrada,
                "precio_actual": precio_actual,
                "auto_ejecutar": True
            })

    return alertas

def ejecutar_venta(cartera, ticker, precio_actual, motivo):
    """Ejecuta venta automatica: libera capital y registra."""
    if ticker not in cartera["posiciones"]:
        return False

    pos = cartera["posiciones"][ticker]
    capital_liberado = pos.get("capital", 0)

    # Actualizar capital
    cartera["capital_disponible"] += capital_liberado

    # Registrar en historial
    cartera["historial"].append({
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "accion": "VENTA",
        "ticker": ticker,
        "precio_entrada": pos["precio_entrada"],
        "precio_salida": precio_actual,
        "capital_liberado": capital_liberado,
        "motivo": motivo
    })

    # Eliminar posicion
    del cartera["posiciones"][ticker]

    return True

def ejecutar_compra(cartera, ticker, precio, capital=MAX_POR_ACCION):
    """Ejecuta compra automatica: reserva capital y registra."""
    if capital > cartera["capital_disponible"]:
        return False, "Capital insuficiente"
    if len(cartera["posiciones"]) >= MAX_POSICIONES:
        return False, "Cartera llena"

    cantidad = capital / precio

    cartera["posiciones"][ticker] = {
        "precio_entrada": precio,
        "cantidad": cantidad,
        "capital": capital,
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "precio_actual": precio
    }

    cartera["capital_disponible"] -= capital
    cartera["compras_esta_semana"] += 1

    cartera["historial"].append({
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "accion": "COMPRA",
        "ticker": ticker,
        "precio": precio,
        "cantidad": cantidad,
        "capital": capital
    })

    return True, "OK"

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="🇪🇺 Eurobot", layout="wide")
st.title("🇪🇺 Eurobot: Pescador Autónomo Europeo")
st.write(f"**Capital:** {CAPITAL_TOTAL:,.0f}€ | **Máx/posición:** {MAX_POR_ACCION:,.0f}€ | **Máx posiciones:** {MAX_POSICIONES} | **Stop-loss:** {STOP_LOSS_PCT}%")
st.write(f"**Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
st.write("---")

# Cargar datos
cartera = cargar_cartera()

# Verificar reset semanal
semana_actual = datetime.now().strftime("%Y-W%U")
if cartera.get("semana_actual") != semana_actual:
    cartera["semana_actual"] = semana_actual
    cartera["compras_esta_semana"] = 0
    guardar_cartera(cartera)

# ============================================================================
# PESTANAS
# ============================================================================
pestaña1, pestaña2, pestaña3 = st.tabs([
    "🤖 Bot Autónomo",
    "📊 Análisis de Universo", 
    "⚙️ Configuración"
])

# ============================================================================
# PESTAÑA 1: BOT AUTONOMO
# ============================================================================
with pestaña1:
    st.subheader("🤖 Estado del Bot")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Capital Total", f"{cartera['capital_total']:,.0f}€")
    col2.metric("Capital Disponible", f"{cartera['capital_disponible']:,.0f}€")
    col3.metric("Posiciones", f"{len(cartera['posiciones'])}/{MAX_POSICIONES}")
    col4.metric("Compras Semana", f"{cartera['compras_esta_semana']}/{COMPRAS_SEMANALES_MAX}")

    st.write("---")

    # MODO AUTOMÁTICO vs MANUAL
    modo_auto = st.toggle("🤖 Modo Automático (ejecuta ventas/compras sin confirmar)", value=False, key="modo_auto")
    if modo_auto:
        st.warning("⚠️ MODO AUTÓNOMO: El bot ejecutará ventas y compras automáticamente. Revisa el historial.")

    st.write("---")

    # Botón ejecutar análisis
    if st.button("🔄 Ejecutar Análisis Completo", type="primary"):
        with st.spinner("Descargando datos de mercado..."):
            datos_batch = descargar_datos_batch(TODOS_TICKERS, period="3mo")

        if datos_batch.empty:
            st.error("❌ No se pudieron descargar datos")
        else:
            resultados = []
            barra = st.progress(0)

            for i, ticker in enumerate(TODOS_TICKERS):
                barra.progress(int((i / len(TODOS_TICKERS)) * 100))
                try:
                    h = extraer_historial(datos_batch, ticker)
                    if h.empty or len(h) < 50:
                        continue

                    precio = h["Close"].iloc[-1]
                    if pd.isna(precio) or precio <= 0:
                        continue

                    metricas = calcular_metricas(h, precio, ticker)
                    if not metricas:
                        continue

                    score, motivos = calcular_score(metricas)

                    resultados.append({
                        "Ticker": ticker,
                        "Score": score,
                        "Precio": precio,
                        "PrecioStr": f"{precio:.2f}€",
                        "Tendencia": "✅ Alcista" if metricas["tendencia_alcista"] else "❌ Bajista",
                        "TendenciaBool": metricas["tendencia_alcista"],
                        "Momentum": f"{metricas['momentum']:.1f}%",
                        "MomentumNum": metricas['momentum'],
                        "Upside": f"{metricas['upside']:.1f}%" if metricas['upside'] else "N/A",
                        "UpsideNum": metricas['upside'],
                        "SMA10": f"{metricas['sma10']:.2f}",
                        "SMA50": f"{metricas['sma50']:.2f}",
                        "Motivos": " | ".join(motivos)
                    })
                except:
                    pass

            barra.empty()

            if resultados:
                df_resultados = pd.DataFrame(resultados)
                df_resultados = df_resultados.sort_values("Score", ascending=False)

                st.write("### 🏆 Ranking del Universo")
                st.dataframe(df_resultados[["Ticker", "Score", "PrecioStr", "Tendencia", "Momentum", "Upside", "Motivos"]], 
                           use_container_width=True)

                # Identificar top 10
                top10 = df_resultados.head(10)
                st.write("### 🎯 Top 10 Oportunidades")
                st.dataframe(top10[["Ticker", "Score", "PrecioStr", "Tendencia", "Momentum", "Upside"]], 
                           use_container_width=True)

                # Actualizar precios actuales en cartera
                for _, row in df_resultados.iterrows():
                    if row["Ticker"] in cartera["posiciones"]:
                        cartera["posiciones"][row["Ticker"]]["precio_actual"] = row["Precio"]

                # Evaluar posiciones actuales
                if cartera["posiciones"]:
                    st.write("---")
                    st.write("### 🚨 Evaluación de Posiciones Actuales")

                    datos_activos = {}
                    for _, row in df_resultados.iterrows():
                        datos_activos[row["Ticker"]] = {
                            "tendencia_alcista": row["TendenciaBool"],
                            "score": row["Score"]
                        }

                    alertas = evaluar_posiciones(cartera, datos_activos)

                    if alertas:
                        for alerta in alertas:
                            if alerta["tipo"] == "STOP_LOSS":
                                st.error(f"🛑 {alerta['ticker']}: {alerta['motivo']} | "
                                        f"Entrada: {alerta['precio_entrada']:.2f}€ | "
                                        f"Actual: {alerta['precio_actual']:.2f}€")
                                if modo_auto:
                                    ejecutar_venta(cartera, alerta['ticker'], alerta['precio_actual'], alerta['motivo'])
                                    st.success(f"✅ VENTA AUTOMÁTICA ejecutada: {alerta['ticker']}")
                            elif alerta["tipo"] == "TENDENCIA_ROTA":
                                st.warning(f"⚠️ {alerta['ticker']}: {alerta['motivo']} | "
                                          f"Entrada: {alerta['precio_entrada']:.2f}€ | "
                                          f"Actual: {alerta['precio_actual']:.2f}€")
                                if modo_auto:
                                    ejecutar_venta(cartera, alerta['ticker'], alerta['precio_actual'], alerta['motivo'])
                                    st.success(f"✅ VENTA AUTOMÁTICA ejecutada: {alerta['ticker']}")
                    else:
                        st.success("✅ Todas las posiciones están dentro de parámetros")

                # Propuestas de compra
                st.write("---")
                st.write("### 💰 Propuestas de Compra")

                puede_comprar, compras_hechas = puede_comprar_esta_semana(cartera)
                posiciones_actuales = set(cartera["posiciones"].keys())

                if not puede_comprar:
                    st.info(f"⏳ Limite de compras semanal alcanzado: {compras_hechas}/{COMPRAS_SEMANALES_MAX}")
                elif len(cartera["posiciones"]) >= MAX_POSICIONES:
                    st.info(f"📊 Cartera llena: {len(cartera['posiciones'])}/{MAX_POSICIONES} posiciones")

                    # Sugerir sustitución
                    top_no_en_cartera = [t for t in top10["Ticker"].tolist() 
                                        if t not in posiciones_actuales][:COMPRAS_SEMANALES_MAX]

                    if top_no_en_cartera:
                        st.write("**Sustituciones sugeridas:**")
                        for nuevo in top_no_en_cartera:
                            # Encontrar la peor posición actual
                            peor_ticker = min(cartera["posiciones"].keys(), 
                                            key=lambda x: datos_activos.get(x, {}).get("score", 0))
                            peor_score = datos_activos.get(peor_ticker, {}).get("score", 0)
                            nuevo_score = datos_activos.get(nuevo, {}).get("score", 0)

                            if nuevo_score > peor_score:
                                st.write(f"🔄 Vender {peor_ticker} (Score {peor_score}) → Comprar {nuevo} (Score {nuevo_score})")
                                if modo_auto:
                                    precio_nuevo = df_resultados[df_resultados["Ticker"] == nuevo]["Precio"].iloc[0]
                                    ejecutar_venta(cartera, peor_ticker, 
                                                   cartera["posiciones"][peor_ticker].get("precio_actual", 0),
                                                   f"Sustitución por {nuevo}")
                                    ejecutar_compra(cartera, nuevo, precio_nuevo)
                                    st.success(f"✅ SUSTITUCIÓN AUTOMÁTICA: {peor_ticker} → {nuevo}")
                            else:
                                st.write(f"⏸️ {nuevo} no supera a {peor_ticker}, no se sustituye")
                    else:
                        st.info("No hay mejores oportunidades fuera de cartera")
                else:
                    # Compras directas
                    top_no_en_cartera = [t for t in top10["Ticker"].tolist() 
                                        if t not in posiciones_actuales][:COMPRAS_SEMANALES_MAX]

                    if top_no_en_cartera:
                        st.write(f"**Compras recomendadas (max {COMPRAS_SEMANALES_MAX} esta semana):**")
                        for ticker in top_no_en_cartera:
                            row = df_resultados[df_resultados["Ticker"] == ticker].iloc[0]
                            st.success(f"🟢 {ticker}: Score {row['Score']}/10 | {row['PrecioStr']} | "
                                      f"Momentum: {row['Momentum']} | Upside: {row['Upside']}")
                            if modo_auto:
                                ok, msg = ejecutar_compra(cartera, ticker, row["Precio"])
                                if ok:
                                    st.success(f"✅ COMPRA AUTOMÁTICA ejecutada: {ticker}")
                                else:
                                    st.error(f"❌ Error compra {ticker}: {msg}")
                    else:
                        st.info("Todas las top oportunidades ya están en cartera")

                # Guardar cartera tras análisis
                guardar_cartera(cartera)
            else:
                st.warning("No se pudieron analizar activos")

    # Mostrar cartera actual con P&L
    st.write("---")
    st.write("### 📁 Cartera Actual")

    if cartera["posiciones"]:
        datos_pos = []
        for ticker, pos in cartera["posiciones"].items():
            precio_entrada = pos["precio_entrada"]
            precio_actual = pos.get("precio_actual", precio_entrada)
            cantidad = pos.get("cantidad", 0)
            capital = pos.get("capital", 0)

            valor_actual = precio_actual * cantidad if cantidad > 0 else capital
            pnl_valor = valor_actual - capital
            pnl_pct = ((precio_actual - precio_entrada) / precio_entrada * 100) if precio_entrada > 0 else 0

            datos_pos.append({
                "Ticker": ticker,
                "Precio Entrada": f"{precio_entrada:.2f}€",
                "Precio Actual": f"{precio_actual:.2f}€" if precio_actual != precio_entrada else "—",
                "Cantidad": f"{cantidad:.4f}",
                "Capital Invertido": f"{capital:.2f}€",
                "Valor Actual": f"{valor_actual:.2f}€",
                "P&L": f"{pnl_valor:+.2f}€ ({pnl_pct:+.2f}%)"
            })

        df_pos = pd.DataFrame(datos_pos)
        st.dataframe(df_pos, use_container_width=True)

        # Totales
        total_invertido = sum(p["capital"] for p in cartera["posiciones"].values())
        total_actual = sum(p.get("precio_actual", p["precio_entrada"]) * p.get("cantidad", 0) 
                         for p in cartera["posiciones"].values())
        total_pnl = total_actual - total_invertido

        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("Total Invertido", f"{total_invertido:.2f}€")
        col_t2.metric("Valor Actual", f"{total_actual:.2f}€")
        col_t3.metric("P&L Total", f"{total_pnl:+.2f}€", delta=f"{total_pnl/total_invertido*100:+.2f}%" if total_invertido > 0 else "0%")
    else:
        st.info("Cartera vacía. Ejecuta el análisis para empezar.")

    # Historial de operaciones
    if cartera["historial"]:
        st.write("---")
        st.write("### 📜 Historial de Operaciones")
        df_hist = pd.DataFrame(cartera["historial"][-20:])  # Últimas 20
        st.dataframe(df_hist, use_container_width=True)

    # Panel de persistencia
    with st.expander("💾 Estado de Persistencia"):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.write(f"**Principal:** {'✅' if os.path.exists(DB_FILE) else '❌'}")
            st.write(f"**Backup:** {'✅' if os.path.exists(DB_BACKUP) else '❌'}")
        with col_p2:
            if st.button("🔄 Forzar Guardado"):
                guardar_cartera(cartera)
                st.success("✅ Cartera guardada")
        with col_p3:
            if st.button("📥 Exportar CSV"):
                if cartera["posiciones"]:
                    df_export = pd.DataFrame(cartera["posiciones"]).T
                    csv = df_export.to_csv()
                    st.download_button("Descargar", csv, "eurobot_cartera.csv", "text/csv")
                else:
                    st.warning("Cartera vacía")

# ============================================================================
# PESTAÑA 2: ANALISIS DE UNIVERSO
# ============================================================================
with pestaña2:
    st.subheader("📊 Análisis Individual")

    ticker_input = st.text_input("Ticker europeo:", placeholder="Ej: SAP.DE, ASML.AS, ITX.MC...")

    if st.button("🔍 Analizar") and ticker_input.strip():
        ticker = ticker_input.strip().upper()
        with st.spinner(f"Analizando {ticker}..."):
            try:
                h = yf.Ticker(ticker).history(period="3mo", interval="1d")
                if h.empty or len(h) < 50:
                    st.error("Datos insuficientes")
                else:
                    precio = h["Close"].iloc[-1]
                    metricas = calcular_metricas(h, precio, ticker)
                    score, motivos = calcular_score(metricas)

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Precio", f"{precio:.2f}€")
                    c2.metric("Score", f"{score}/10")
                    c3.metric("Momentum", f"{metricas['momentum']:.1f}%")

                    c4, c5, c6 = st.columns(3)
                    c4.metric("SMA10", f"{metricas['sma10']:.2f}")
                    c5.metric("SMA50", f"{metricas['sma50']:.2f}")
                    c6.metric("Upside", f"{metricas['upside']:.1f}%" if metricas['upside'] else "N/A")

                    if metricas["tendencia_alcista"]:
                        st.success("✅ Tendencia Alcista")
                    else:
                        st.error("❌ Tendencia Bajista")

                    st.write(f"**Motivos:** {' | '.join(motivos)}")
            except Exception as e:
                st.error(f"Error: {e}")

# ============================================================================
# PESTAÑA 3: CONFIGURACION
# ============================================================================
with pestaña3:
    st.subheader("⚙️ Configuración y Listas")

    for nombre, tickers in UNIVERSO_EUROPEO.items():
        with st.expander(f"{nombre} ({len(tickers)} tickers)"):
            st.write(", ".join(tickers))

    st.write("---")
    st.write(f"**Total tickers en universo:** {len(TODOS_TICKERS)}")
    st.write(f"**Tickers únicos:** {len(set(TODOS_TICKERS))}")

    if st.button("🗑️ Resetear Cartera"):
        cartera = {
            "capital_total": CAPITAL_TOTAL,
            "capital_disponible": CAPITAL_TOTAL,
            "posiciones": {},
            "historial": [],
            "compras_esta_semana": 0,
            "semana_actual": datetime.now().strftime("%Y-W%U")
        }
        guardar_cartera(cartera)
        st.success("Cartera reseteada")
        st.rerun()

st.write("---")
st.caption("Eurobot v1.0 | Pescador Autónomo Europeo | Streamlit + yFinance")
