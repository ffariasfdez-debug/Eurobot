

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
LISTAS_FILE = 'eurobot_listas.json'
CAPITAL_TOTAL = 30000
MAX_POSICIONES = 10
MAX_POR_COMPRA = 2000
MAX_COMPRAS_SEMANA = 2

# Listas base actualizadas (junio 2026)
LISTAS_DEFECTO = {
    "DAX 40": [
        "SAP.DE", "SIE.DE", "ALV.DE", "ADS.DE", "BAS.DE", "BAYN.DE", "BMW.DE", 
        "CON.DE", "DB1.DE", "DBK.DE", "DPW.DE", "DTE.DE", "EOAN.DE", "FME.DE", 
        "FRE.DE", "HEI.DE", "HEN3.DE", "IFX.DE", "MBG.DE", "MRK.DE", "MTX.DE", 
        "MUV2.DE", "P911.DE", "RHM.DE", "RWE.DE", "SHL.DE", "SRT.DE", "SY1.DE", 
        "VOW3.DE", "ZAL.DE", "AIR.DE", "BNR.DE", "CBK.DE", "ENR.DE", "FNTN.DE", 
        "G1A.DE", "HNR1.DE", "MTU.DE", "QIA.DE", "BEI.DE"
    ],
    "EuroStoxx 50": [
        "MC.PA", "ASML.AS", "SAP.DE", "OR.PA", "SIE.DE", "TTE.PA", "SAN.PA", 
        "SU.PA", "AIR.PA", "AI.PA", "EL.PA", "BAS.DE", "BAYN.DE", "ALV.DE", 
        "ADS.DE", "MBG.DE", "BMW.DE", "DBK.DE", "DPW.DE", "CON.DE", "HEN3.DE", 
        "FME.DE", "DB1.DE", "FRE.DE", "MRK.DE", "IFX.DE", "MUV2.DE", "RHM.DE", 
        "BEI.DE", "BNR.DE", "EOAN.DE", "HEI.DE", "MTX.DE", "RWE.DE", "ENEL.MI", 
        "ISP.MI", "UCG.MI", "ENI.MI", "STLAM.MI", "PRX.AS"
    ],
    "IBEX 35": [
        "SAN", "BBVA", "ITX", "IBE", "TEF", "REP", "AENA", "AMS", "COL", "FER", 
        "GRF", "IAG", "MAP", "MRL", "NTGY", "REE", "SGRE", "SLR", "ACS", "ACX", 
        "BKT", "CABK", "CLNX", "ELE", "ENG", "FDR", "GAM", "IDR", "LOG", "MEL", 
        "MGA", "PAP", "PHM", "PSG", "ROVI", "SAB", "SCYR", "TL5", "UNI", "VIS"
    ]
}

# ============================================================================
# PERSISTENCIA
# ============================================================================
def cargar_datos():
    if not os.path.exists(DB_FILE):
        return {
            "capital_disponible": CAPITAL_TOTAL,
            "posiciones": {},
            "historial": [],
            "compras_semana": {},
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

def cargar_listas():
    if not os.path.exists(LISTAS_FILE):
        return LISTAS_DEFECTO.copy()
    try:
        with open(LISTAS_FILE, 'r') as f:
            return json.load(f)
    except:
        return LISTAS_DEFECTO.copy()

def guardar_listas(listas):
    with open(LISTAS_FILE, 'w') as f:
        json.dump(listas, f, indent=2)

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================
def get_universo_consolidado(listas):
    """Crea universo único sin duplicados"""
    universo = []
    vistos = set()
    for lista in listas.values():
        for ticker in lista:
            ticker_upper = ticker.upper().strip()
            if ticker_upper not in vistos:
                vistos.add(ticker_upper)
                universo.append(ticker)
    return universo

def get_semana_actual():
    return datetime.now().strftime("%Y-W%U")

def compras_esta_semana(datos):
    semana = get_semana_actual()
    return datos["compras_semana"].get(semana, 0)

def puede_comprar(datos):
    semana = get_semana_actual()
    compras = datos["compras_semana"].get(semana, 0)
    if compras >= MAX_COMPRAS_SEMANA:
        return False, f"Límite semanal: {compras}/{MAX_COMPRAS_SEMANA}"
    if len(datos["posiciones"]) >= MAX_POSICIONES:
        return False, f"Cartera llena: {len(datos['posiciones'])}/{MAX_POSICIONES}"
    if datos["capital_disponible"] < MAX_POR_COMPRA:
        return False, f"Capital insuficiente: {datos['capital_disponible']:.0f}€"
    return True, "OK"

def registrar_compra(datos, ticker, precio, cantidad, invertido, nombre):
    semana = get_semana_actual()
    datos["compras_semana"][semana] = datos["compras_semana"].get(semana, 0) + 1
    datos["posiciones"][ticker] = {
        "precio": round(precio, 2),
        "cantidad": round(cantidad, 4),
        "fecha": datetime.now().strftime('%d/%m/%Y'),
        "invertido": round(invertido, 2),
        "nombre": nombre
    }
    datos["capital_disponible"] -= invertido
    datos["historial"].append(
        f"✅ COMPRA: {nombre} ({ticker}) @ {precio:.2f}€ | {cantidad:.4f} uds | {invertido:.0f}€ | {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    guardar_datos(datos)

def registrar_venta(datos, ticker, precio_actual, nombre, motivo="Tendencia rota"):
    if ticker in datos["posiciones"]:
        pos = datos["posiciones"][ticker]
        valor_actual = pos["cantidad"] * precio_actual
        pnl = valor_actual - pos["invertido"]
        pnl_pct = (pnl / pos["invertido"]) * 100 if pos["invertido"] > 0 else 0

        datos["capital_disponible"] += valor_actual
        del datos["posiciones"][ticker]

        emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⬜"
        datos["historial"].append(
            f"{emoji} VENTA: {nombre} ({ticker}) @ {precio_actual:.2f}€ | P&L: {pnl:+.2f}€ ({pnl_pct:+.1f}%) | {motivo} | {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        guardar_datos(datos)
        return True, pnl
    return False, 0

# ============================================================================
# ANALISIS TECNICO
# ============================================================================
def get_scalar(val):
    if hasattr(val, 'item'):
        return float(val.item())
    elif isinstance(val, pd.Series):
        return float(val.iloc[0])
    return float(val)

def analizar_accion(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df.empty or len(df) < 50:
            return None, "Sin datos"

        # Manejar MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            close_col = ('Close', ticker) if ('Close', ticker) in df.columns else 'Close'
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
        rsi_valor = get_scalar(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

        sma10_val = get_scalar(sma10)
        sma50_val = get_scalar(sma50)
        precio_val = get_scalar(precio_actual)

        tendencia_alcista = sma10_val > sma50_val
        fuerza = "FUERTE" if precio_val > sma10_val else "DEBIL"

        # Obtener nombre de la empresa
        try:
            t = yf.Ticker(ticker)
            info = t.info
            nombre = info.get('shortName', ticker)
        except:
            nombre = ticker

        return {
            "ticker": ticker,
            "nombre": nombre,
            "precio": round(precio_val, 2),
            "sma10": round(sma10_val, 2),
            "sma50": round(sma50_val, 2),
            "tendencia": tendencia_alcista,
            "fuerza": fuerza,
            "rsi": round(rsi_valor, 1),
            "score": 0  # Se calcula después
        }, "OK"
    except Exception as e:
        return None, str(e)

def calcular_score(accion):
    score = 0
    motivos = []

    if accion["tendencia"]:
        score += 5
        motivos.append("Tendencia alcista (+5)")

    if accion["fuerza"] == "FUERTE":
        score += 3
        motivos.append("Precio > SMA10 (+3)")

    if 30 < accion["rsi"] < 70:
        score += 2
        motivos.append(f"RSI {accion['rsi']:.0f} neutral (+2)")
    elif accion["rsi"] < 30:
        score += 1
        motivos.append(f"RSI {accion['rsi']:.0f} sobreventa (+1)")

    return score, motivos

# ============================================================================
# LOGICA AUTONOMA
# ============================================================================
def ejecutar_logica_autonoma(datos, listas):
    acciones = []
    universo = get_universo_consolidado(listas)

    # 1. Analizar todas las acciones
    resultados = {}
    for ticker in universo:
        analisis, error = analizar_accion(ticker)
        if analisis:
            score, motivos = calcular_score(analisis)
            analisis["score"] = score
            analisis["motivos"] = motivos
            resultados[ticker] = analisis
        else:
            acciones.append(f"⚠️ {ticker}: {error}")

    if not resultados:
        return acciones + ["❌ No se pudo analizar ninguna acción"]

    # 2. VENDER posiciones que ya no son alcistas
    for ticker in list(datos["posiciones"].keys()):
        if ticker in resultados:
            if not resultados[ticker]["tendencia"]:
                ok, pnl = registrar_venta(
                    datos, ticker, resultados[ticker]["precio"], 
                    datos["posiciones"][ticker]["nombre"], "Tendencia rota"
                )
                if ok:
                    acciones.append(f"🗑️ VENDIDO {resultados[ticker]['nombre']}: Tendencia rota")
        else:
            # Si no hay datos, mantener por ahora
            pass

    # 3. Ordenar por score y comprar las mejores
    tickers_ordenados = sorted(resultados.keys(), key=lambda x: resultados[x]["score"], reverse=True)

    compras_realizadas = 0
    for ticker in tickers_ordenados:
        if compras_realizadas >= 2:  # Máximo 2 por ejecución
            break

        if ticker in datos["posiciones"]:
            continue  # Ya tenemos esta posición

        if not resultados[ticker]["tendencia"]:
            continue  # No es alcista

        if resultados[ticker]["score"] < 5:
            continue  # Score insuficiente

        puede, msg = puede_comprar(datos)
        if not puede:
            acciones.append(f"⏳ {resultados[ticker]['nombre']}: {msg}")
            continue

        precio = resultados[ticker]["precio"]
        cantidad = MAX_POR_COMPRA / precio
        invertido = MAX_POR_COMPRA
        nombre = resultados[ticker]["nombre"]

        registrar_compra(datos, ticker, precio, cantidad, invertido, nombre)
        acciones.append(
            f"💰 COMPRADO {nombre} ({ticker}): Score {resultados[ticker]['score']}/10 | {invertido:.0f}€ @ {precio:.2f}€"
        )
        compras_realizadas += 1

    return acciones

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="🇪🇺 Eurobot Autónomo", layout="wide")

st.title("🇪🇺 Eurobot Autónomo")
st.write(f"**Capital:** {CAPITAL_TOTAL:,.0f}€ | **Máx:** {MAX_POSICIONES} pos | **Compra:** {MAX_POR_COMPRA:,.0f}€ | **Semana:** {MAX_COMPRAS_SEMANA} compras")
st.write("---")

# Cargar datos y listas
datos = cargar_datos()
listas = cargar_listas()

# PESTAÑAS
pestaña_bot, pestaña_cartera, pestaña_config = st.tabs([
    "🤖 Bot Autónomo", 
    "📊 Cartera", 
    "⚙️ Configuración de Listas"
])

# ============================================================================
# PESTAÑA 1: BOT AUTONOMO
# ============================================================================
with pestaña_bot:
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Ejecutar Bot", type="primary"):
            with st.spinner("🤖 Analizando mercados..."):
                acciones = ejecutar_logica_autonoma(datos, listas)

            # Recargar datos después de ejecución
            datos = cargar_datos()

            if acciones:
                st.write("### 📝 Acciones del Bot")
                for accion in acciones:
                    st.write(accion)
            else:
                st.info("Sin acciones esta vez.")

    with col2:
        st.metric("Capital Disponible", f"{datos['capital_disponible']:,.0f}€")

    with col3:
        st.metric("Posiciones", f"{len(datos['posiciones'])}/{MAX_POSICIONES}")

    # Botón de reset visible
    st.write("---")
    col_reset, col_info = st.columns([1, 3])
    with col_reset:
        if st.button("🗑️ BORRAR CARTERA COMPLETA", type="secondary"):
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            st.success("✅ Cartera borrada completamente. Recarga la página.")
            st.rerun()
    with col_info:
        st.info("⚠️ Esto borra todas las posiciones y el historial. Usa solo si necesitas empezar de cero.")
        st.metric("Capital Disponible", f"{datos['capital_disponible']:,.0f}€")

    with col3:
        st.metric("Posiciones", f"{len(datos['posiciones'])}/{MAX_POSICIONES}")

    # Métricas de cartera
    if datos["posiciones"]:
        pnl_total = 0
        for ticker, pos in datos["posiciones"].items():
            try:
                df = yf.download(ticker, period="1d", interval="1m", progress=False)
                if not df.empty:
                    close_col = 'Close'
                    if isinstance(df.columns, pd.MultiIndex):
                        close_col = ('Close', ticker) if ('Close', ticker) in df.columns else 'Close'
                    precio_actual = get_scalar(df[close_col].iloc[-1])
                    valor_actual = pos["cantidad"] * precio_actual
                    pnl_total += valor_actual - pos["invertido"]
            except:
                pass

        st.metric("P&L Total", f"{pnl_total:+.2f}€", f"{pnl_total/CAPITAL_TOTAL*100:+.1f}%")

# ============================================================================
# PESTAÑA 2: CARTERA
# ============================================================================
with pestaña_cartera:
    st.write(f"### 📈 Cartera ({len(datos['posiciones'])}/{MAX_POSICIONES} posiciones)")

    # Botón de reset visible
    col_reset, col_info = st.columns([1, 3])
    with col_reset:
        if st.button("🗑️ BORRAR CARTERA COMPLETA", key="reset_cartera"):
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            st.success("✅ Cartera borrada. Recarga la página.")
            st.rerun()
    with col_info:
        st.info("⚠️ Borra todas las posiciones y reinicia el capital a 30.000€")

    st.write("---")

    if datos["posiciones"]:
        cartera_data = []
        for ticker, pos in datos["posiciones"].items():
            try:
                # Descargar datos para calcular rentabilidades
                df_hoy = yf.download(ticker, period="5d", interval="1d", progress=False)

                if not df_hoy.empty and len(df_hoy) >= 2:
                    close_col = 'Close'
                    open_col = 'Open'
                    if isinstance(df_hoy.columns, pd.MultiIndex):
                        close_col = ('Close', ticker) if ('Close', ticker) in df_hoy.columns else 'Close'
                        open_col = ('Open', ticker) if ('Open', ticker) in df_hoy.columns else 'Open'

                    precios = df_hoy[close_col].squeeze()
                    aperturas = df_hoy[open_col].squeeze()

                    if isinstance(precios, pd.DataFrame): precios = precios.iloc[:, 0]
                    if isinstance(aperturas, pd.DataFrame): aperturas = aperturas.iloc[:, 0]

                    precio_apertura_hoy = get_scalar(aperturas.iloc[-1])
                    precio_actual = get_scalar(precios.iloc[-1])
                else:
                    precio_actual = pos["precio"]
                    precio_apertura_hoy = pos["precio"]

                precio_entrada = pos["precio"]
                nombre = pos.get("nombre", ticker)

                # Rentabilidad del día (desde apertura)
                rend_dia_eur = pos["cantidad"] * (precio_actual - precio_apertura_hoy)
                rend_dia_pct = ((precio_actual - precio_apertura_hoy) / precio_apertura_hoy) * 100 if precio_apertura_hoy > 0 else 0

                # Rentabilidad acumulada (desde compra)
                rend_acum_eur = pos["cantidad"] * (precio_actual - precio_entrada)
                rend_acum_pct = ((precio_actual - precio_entrada) / precio_entrada) * 100 if precio_entrada > 0 else 0

                # Stop Loss y Take Profit (basado en ATR)
                try:
                    df_atr = yf.download(ticker, period="1mo", interval="1d", progress=False)
                    if not df_atr.empty and len(df_atr) >= 14:
                        high_col = 'High'
                        low_col = 'Low'
                        close_col_atr = 'Close'
                        if isinstance(df_atr.columns, pd.MultiIndex):
                            high_col = ('High', ticker) if ('High', ticker) in df_atr.columns else 'High'
                            low_col = ('Low', ticker) if ('Low', ticker) in df_atr.columns else 'Low'
                            close_col_atr = ('Close', ticker) if ('Close', ticker) in df_atr.columns else 'Close'

                        highs = df_atr[high_col].squeeze()
                        lows = df_atr[low_col].squeeze()
                        closes = df_atr[close_col_atr].squeeze()

                        if isinstance(highs, pd.DataFrame): highs = highs.iloc[:, 0]
                        if isinstance(lows, pd.DataFrame): lows = lows.iloc[:, 0]
                        if isinstance(closes, pd.DataFrame): closes = closes.iloc[:, 0]

                        high_low = highs - lows
                        high_close = abs(highs - closes.shift())
                        low_close = abs(lows - closes.shift())
                        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                        atr_val = get_scalar(tr.rolling(window=14).mean().iloc[-1])

                        stop_loss = precio_entrada - (atr_val * 2)
                        take_profit = precio_entrada + (atr_val * 3)
                    else:
                        stop_loss = precio_entrada * 0.95
                        take_profit = precio_entrada * 1.15
                except:
                    stop_loss = precio_entrada * 0.95
                    take_profit = precio_entrada * 1.15

                color_dia = "🟢" if rend_dia_pct >= 0 else "🔴"
                color_acum = "🟢" if rend_acum_pct >= 0 else "🔴"

                cartera_data.append({
                    "Nombre": nombre,
                    "Ticker": ticker,
                    "Fecha Compra": pos["fecha"],
                    "Precio Entrada": f"{precio_entrada:.2f}€",
                    "Precio Actual": f"{precio_actual:.2f}€",
                    "Cantidad": f"{pos['cantidad']:.4f}",
                    "Invertido": f"{pos['invertido']:.0f}€",
                    f"Rend. Día {color_dia}": f"{rend_dia_pct:+.2f}% ({rend_dia_eur:+.2f}€)",
                    f"Rend. Acum. {color_acum}": f"{rend_acum_pct:+.2f}% ({rend_acum_eur:+.2f}€)",
                    "Stop Loss": f"{stop_loss:.2f}€",
                    "Take Profit": f"{take_profit:.2f}€",
                    "Dist. SL": f"{((precio_actual - stop_loss) / precio_actual * 100):.1f}%",
                    "Dist. TP": f"{((take_profit - precio_actual) / precio_actual * 100):.1f}%"
                })
            except Exception as e:
                st.warning(f"Error {ticker}: {e}")
                cartera_data.append({
                    "Nombre": pos.get("nombre", ticker),
                    "Ticker": ticker,
                    "Fecha Compra": pos["fecha"],
                    "Precio Entrada": f"{pos['precio']:.2f}€",
                    "Precio Actual": "Error",
                    "Cantidad": f"{pos['cantidad']:.4f}",
                    "Invertido": f"{pos['invertido']:.0f}€",
                    "Rend. Día": "N/A",
                    "Rend. Acum.": "N/A",
                    "Stop Loss": "N/A",
                    "Take Profit": "N/A",
                    "Dist. SL": "N/A",
                    "Dist. TP": "N/A"
                })

        df_cartera = pd.DataFrame(cartera_data)
        st.dataframe(df_cartera, use_container_width=True)

        # Resumen
        if cartera_data:
            total_acum_pct = 0
            total_acum_eur = 0
            total_dia_pct = 0
            total_dia_eur = 0
            acums = []

            for row in cartera_data:
                try:
                    acum_key = [k for k in row.keys() if "Rend. Acum." in k][0]
                    acum_str = row[acum_key]
                    acum_pct = float(acum_str.split('%')[0])
                    acum_eur = float(acum_str.split('(')[1].split('€')[0])
                    total_acum_pct += acum_pct
                    total_acum_eur += acum_eur
                    acums.append(acum_pct)

                    dia_key = [k for k in row.keys() if "Rend. Día" in k][0]
                    dia_str = row[dia_key]
                    dia_pct = float(dia_str.split('%')[0])
                    dia_eur = float(dia_str.split('(')[1].split('€')[0])
                    total_dia_pct += dia_pct
                    total_dia_eur += dia_eur
                except:
                    pass

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                st.metric("Rent. Acumulada", f"{total_acum_pct:+.2f}%", f"{total_acum_eur:+.2f}€")
            with col_r2:
                st.metric("Rent. Día", f"{total_dia_pct:+.2f}%", f"{total_dia_eur:+.2f}€")
            with col_r3:
                st.metric("Mejor", f"{max(acums):+.2f}%")
            with col_r4:
                st.metric("Peor", f"{min(acums):+.2f}%")
    else:
        st.info("Cartera vacía. Ejecuta el bot para comprar.")

    # Historial
    st.write("---")
    st.write("### 📜 Historial")
    if datos["historial"]:
        for op in reversed(datos["historial"][-20:]):
            st.write(op)
    else:
        st.info("Sin operaciones.")

with pestaña_config:
    st.subheader("⚙️ Gestión de Listas de Acciones")
    st.write("Aquí puedes añadir o quitar acciones de cada índice. Los cambios se guardan automáticamente.")

    for nombre_lista, tickers_lista in listas.items():
        with st.expander(f"📋 {nombre_lista} ({len(tickers_lista)} acciones)"):
            st.write(f"**Acciones actuales:** {', '.join(tickers_lista)}")

            col_del, col_add = st.columns([1, 2])
            with col_del:
                ticker_a_eliminar = st.selectbox(f"Eliminar de {nombre_lista}:", tickers_lista, key=f"del_{nombre_lista}")
                if st.button(f"🗑️ Eliminar", key=f"btn_del_{nombre_lista}"):
                    if ticker_a_eliminar in listas[nombre_lista]:
                        listas[nombre_lista].remove(ticker_a_eliminar)
                        guardar_listas(listas)
                        st.success(f"🗑️ Eliminado {ticker_a_eliminar}")
                        st.rerun()

            with col_add:
                nuevo_ticker = st.text_input(f"Añadir a {nombre_lista}:", key=f"add_{nombre_lista}")
                if st.button(f"➕ Añadir", key=f"btn_add_{nombre_lista}"):
                    if nuevo_ticker and nuevo_ticker.strip().upper() not in [t.upper() for t in listas[nombre_lista]]:
                        listas[nombre_lista].append(nuevo_ticker.strip().upper())
                        guardar_listas(listas)
                        st.success(f"➕ Añadido {nuevo_ticker.strip().upper()}")
                        st.rerun()
                    else:
                        st.error("Vacío o duplicado")

    st.write("---")
    if st.button("🔄 Resetear a Listas por Defecto"):
        listas = LISTAS_DEFECTO.copy()
        guardar_listas(listas)
        st.success("✅ Listas reseteadas")
        st.rerun()

    st.write("---")
    st.write(f"**Universo total:** {len(get_universo_consolidado(listas))} acciones únicas")

st.write("---")
st.caption(f"🇪🇺 Eurobot Autónomo | Última ejecución: {datos.get('ultima_ejecucion', 'Nunca')}")
