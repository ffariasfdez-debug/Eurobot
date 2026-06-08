

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import json
import time
import numpy as np
import os

# ============================================================================
# PERSISTENCIA DE CARTERA
# ============================================================================
CARTERA_FILE = "cartera_guardada.json"
LISTAS_FILE = "listas_guardadas.json"
REGISTRO_FILE = "registro_semanal.json"

def cargar_cartera():
    if os.path.exists(CARTERA_FILE):
        try:
            with open(CARTERA_FILE, "r") as f:
                data = json.load(f)
            if data and len(data) > 0:
                return pd.DataFrame(data)
        except Exception as e:
            st.warning(f"⚠️ Archivo principal corrupto: {e}")
    # Intentar recuperar desde backup
    if os.path.exists(CARTERA_FILE + ".bak"):
        try:
            with open(CARTERA_FILE + ".bak", "r") as f:
                data = json.load(f)
            if data and len(data) > 0:
                st.success(f"✅ Cartera recuperada desde backup ({len(data)} posiciones)")
                return pd.DataFrame(data)
        except:
            pass
    return pd.DataFrame()

def guardar_cartera(df):
    try:
        # Backup previo
        if os.path.exists(CARTERA_FILE):
            with open(CARTERA_FILE, "r") as f_orig:
                contenido = f_orig.read()
            with open(CARTERA_FILE + ".bak", "w") as f_bak:
                f_bak.write(contenido)
        # Guardar nuevo
        df.to_json(CARTERA_FILE, orient="records", date_format="iso")
    except Exception as e:
        st.error(f"Error guardando cartera: {e}")

def cargar_listas():
    if os.path.exists(LISTAS_FILE):
        try:
            with open(LISTAS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return None

def guardar_listas(listas):
    try:
        with open(LISTAS_FILE, "w") as f:
            json.dump(listas, f, indent=2)
    except Exception as e:
        st.error(f"Error guardando listas: {e}")

def cargar_registro():
    if os.path.exists(REGISTRO_FILE):
        try:
            with open(REGISTRO_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def guardar_registro(registro):
    try:
        with open(REGISTRO_FILE, "w") as f:
            json.dump(registro, f, indent=2)
    except Exception as e:
        st.error(f"Error guardando registro: {e}")

# ============================================================================
# CONFIGURACION INICIAL
# ============================================================================
st.set_page_config(page_title="Centro de Mando Financiero", layout="wide")

st.title("🎛️ Centro de Mando Financiero Pro")
st.write(f"**Horizonte:** 4 Años | **Estilo:** Buy & Hold | **Foco:** Robótica & Tech")
st.write(f"**Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
st.write("---")

# ============================================================================
# LISTAS DEFINITIVAS
# ============================================================================
LISTAS_DEFINITIVAS = {
    "🤖 Robótica y Automatización": [
        "ABB", "FANUY", "SIEGY", "YASKY", "ROK", "AME", "FTV", "ETN", "EMR", "DOV",
        "ISRG", "TER", "CGNX", "NVMI", "PTC", "IRBT", "SYM", "DFKCY", "KIGRY",
        "TDY", "KEYS", "ZBRA", "SYK", "GMED", "PRCT", "DE", "CAT", "AGCO", "PCAR",
        "CMI", "ITW", "HON", "OCDO.L", "AUTO.OL"
    ],
    "🧠 IA y Semiconductores": [
        "NVDA", "AMD", "ARM", "AVGO", "TSM", "ASML", "LRCX", "KLAC", "AMAT",
        "ENTG", "MU", "PSTG", "ON", "ADI", "TXN", "NXPI", "MPWR", "STM",
        "MCHP", "ANET"
    ],
    "🛡️ Defensa y Drones": [
        "RTX", "LMT", "GD", "NOC", "GE", "AVAV", "KTOS", "LHX", "HII",
        "TXT", "CW", "BAH", "SAIC", "LDOS", "CACI", "AXON", "KBR", "BWXT"
    ],
    "⚡ Energía, Fotónica y Espacio": [
        "ENPH", "SEDG", "FSLR", "NEE", "HASI", "EVRG", "AES", "FLNC",
        "VST", "IPGP", "COHR", "LITE", "RKLB", "ASTS", "IRDM"
    ],
    "🧬 Biotecnología y Genómica": [
        "VRTX", "ILMN", "CRSP", "EDIT", "BEAM", "NTLA", "PACB", "EXAS",
        "TMO", "DHR", "RGEN", "ZTS", "INCY", "REGN", "MRNA", "LLY"
    ]
}

# MEJORA 1: Eliminado alias ABJ -> ABB (ABJ no es ticker estandar)
TICKER_ALIASES = {}

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def detectar_moneda(ticker):
    ticker_upper = ticker.upper().strip()
    sufijos_eur = [".AS", ".PA", ".DE", ".BR", ".MI", ".MC", ".ST", ".HE", ".CO", ".OL", ".VI", ".LS", ".IR"]
    for sufijo in sufijos_eur:
        if ticker_upper.endswith(sufijo):
            return "EUR"
    if ticker_upper.endswith(".L") or ticker_upper.endswith(".LN"):
        return "GBP"
    return "USD"

def simbolo_moneda(moneda):
    simbolos = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF", "JPY": "¥", "CAD": "C$"}
    return simbolos.get(moneda, "$")

def comprobar_mercado_abierto():
    tz_ny = pytz.timezone("America/New_York")
    hora_ny = datetime.now(tz_ny)
    dia_semana = hora_ny.weekday()
    inicio_mercado = hora_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    fin_mercado = hora_ny.replace(hour=16, minute=0, second=0, microsecond=0)
    return dia_semana <= 4 and inicio_mercado <= hora_ny <= fin_mercado

def calcular_rsi(historial, periodo=14):
    try:
        delta = historial["Close"].diff()
        ganancia = (delta.where(delta > 0, 0)).rolling(window=periodo).mean()
        perdida = (-delta.where(delta < 0, 0)).rolling(window=periodo).mean()
        rs = ganancia / perdida
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    except:
        return 50

def calcular_beta(historial, beta_info=None):
    if beta_info is not None and beta_info > 0 and beta_info < 10:
        return round(beta_info, 2)
    try:
        spy_hist = yf.Ticker("SPY").history(period="1y")
        if spy_hist.empty or len(spy_hist) < 30:
            return estimar_beta_desde_volatilidad(historial)
        stock_recent = historial["Close"].iloc[-90:]
        spy_recent = spy_hist["Close"].iloc[-90:]
        common_idx = stock_recent.index.intersection(spy_recent.index)
        if len(common_idx) < 20:
            return estimar_beta_desde_volatilidad(historial)
        s_prices = stock_recent.loc[common_idx]
        spy_prices = spy_recent.loc[common_idx]
        s_ret = s_prices.pct_change().dropna()
        spy_ret = spy_prices.pct_change().dropna()
        if len(s_ret) < 15 or len(spy_ret) < 15:
            return estimar_beta_desde_volatilidad(historial)
        cov = np.cov(s_ret, spy_ret)[0, 1]
        var_market = np.var(spy_ret)
        if var_market == 0 or np.isnan(cov):
            return estimar_beta_desde_volatilidad(historial)
        beta = cov / var_market
        if abs(beta) > 5 or np.isnan(beta):
            return estimar_beta_desde_volatilidad(historial)
        return round(float(beta), 2)
    except:
        return estimar_beta_desde_volatilidad(historial)

def estimar_beta_desde_volatilidad(historial):
    try:
        retornos = historial["Close"].pct_change().dropna().iloc[-90:]
        if len(retornos) < 20:
            return None
        volatilidad_stock = retornos.std() * np.sqrt(252)
        volatilidad_mercado = 0.16
        beta_estimado = volatilidad_stock / volatilidad_mercado
        if beta_estimado > 5:
            beta_estimado = 5.0
        return round(float(beta_estimado), 2)
    except:
        return None

# ============================================================================
# NUEVO MOTOR DE ANALISIS LIMPIO (v6.1) - CON CONTEXTO DE CAIDA
# ============================================================================

def calcular_metricas_limpias(historial, precio_actual, ticker):
    """Calcula metricas limpias. Devuelve: (crecimiento_anualizado, upside_analista, revenue_growth)"""
    try:
        precio_60d = historial["Close"].iloc[-60] if len(historial) >= 60 else historial["Close"].iloc[0]
        if precio_60d > 0 and precio_actual > 0:
            crec_anual = ((precio_actual / precio_60d) ** (252/60) - 1) * 100
            crec_anual = round(crec_anual, 1)
        else:
            crec_anual = 0.0
    except:
        crec_anual = 0.0

    upside_anal = None
    revenue_growth = None
    try:
        ticker_real = TICKER_ALIASES.get(ticker.upper(), ticker)
        t = yf.Ticker(ticker_real)
        info = t.info
        target = info.get("targetMedianPrice", None)
        if target and target > 0 and precio_actual > 0:
            upside = ((target - precio_actual) / precio_actual) * 100
            if -50 < upside < 50:
                upside_anal = round(upside, 1)
        rev_growth = info.get("revenueGrowth", None)
        if rev_growth is not None and not np.isnan(rev_growth):
            revenue_growth = round(rev_growth * 100, 1)
    except:
        pass

    return crec_anual, upside_anal, revenue_growth


def calcular_confianza_dato(crec_anual, upside_anal, revenue_growth):
    """
    Evalua la coherencia entre fuentes de datos.
    - ALTA: Fuentes alineadas o solo una fuente disponible
    - MEDIA: Divergencia moderada entre fuentes
    - BAJA: Divergencia fuerte (>50%), posible dato contaminado
    """
    fuentes = []
    if crec_anual is not None and crec_anual != 0:
        fuentes.append(("momentum", crec_anual))
    if upside_anal is not None:
        fuentes.append(("target", upside_anal))
    if revenue_growth is not None:
        fuentes.append(("fundamental", revenue_growth))
    
    if len(fuentes) < 2:
        return "ALTA", "Dato unico - sin comparacion"
    
    valores = [v for _, v in fuentes]
    max_val = max(valores)
    min_val = min(valores)
    
    if max_val == 0:
        return "ALTA", "Valores cercanos a cero"
    
    divergencia_pct = abs(max_val - min_val) / abs(max_val) * 100
    
    if divergencia_pct > 50:
        return "BAJA", f"Divergencia {divergencia_pct:.0f}% entre fuentes"
    elif divergencia_pct > 25:
        return "MEDIA", f"Divergencia {divergencia_pct:.0f}% entre fuentes"
    else:
        return "ALTA", f"Fuentes alineadas ({divergencia_pct:.0f}%)"


def calcular_potencial_compuesto(crec_anual, upside_anal, revenue_growth):
    """
    Combina tres fuentes de potencial con ponderacion para Buy & Hold 4Y:
    - 40% momentum 60d (hecho reciente)
    - 30% upside analista (estimacion 12m)
    - 30% revenue growth YoY (fundamental)
    """
    pesos = []
    valores = []
    
    if crec_anual is not None and crec_anual != 0:
        pesos.append(0.40)
        valores.append(crec_anual)
    if upside_anal is not None:
        pesos.append(0.30)
        valores.append(upside_anal)
    if revenue_growth is not None:
        pesos.append(0.30)
        valores.append(revenue_growth)
    
    if not pesos:
        return None
    
    total_pesos = sum(pesos)
    pesos_norm = [p / total_pesos for p in pesos]
    
    potencial = sum(v * p for v, p in zip(valores, pesos_norm))
    return round(potencial, 1)

# ============================================================================
# NUEVAS FUNCIONES v6.1: CONTEXTO DE CAIDA Y CLASIFICACION
# ============================================================================

def analizar_contexto_caida(ticker, cambio_hoy_pct):
    """
    Determina si la caida es idiosincratica, sistemica o tecnica.
    Compara con SPY y con ETF de sector.
    Devuelve: (origen, fortaleza_relativa, mensaje, recomendacion)
    """
    try:
        # Descargar SPY para comparar con mercado
        spy = yf.Ticker("SPY").history(period="5d")
        if len(spy) >= 2:
            cambio_spy = ((spy["Close"].iloc[-1] - spy["Close"].iloc[-2]) / spy["Close"].iloc[-2]) * 100
        else:
            cambio_spy = 0
    except:
        cambio_spy = 0
    
    # Determinar si el mercado se movio fuerte
    mercado_volatil = abs(cambio_spy) > 2
    
    if mercado_volatil:
        diferencia = cambio_hoy_pct - cambio_spy
        if cambio_hoy_pct < cambio_spy - 3:
            return "SISTEMICA", "DEBIL", f"Mercado {cambio_spy:.1f}%, tu caida {cambio_hoy_pct:.1f}% (mucho peor)", "🚩 TRAMPA: Caes mas que el mercado"
        elif cambio_hoy_pct > cambio_spy + 2:
            return "SISTEMICA", "FUERTE", f"Mercado {cambio_spy:.1f}%, tu caida {cambio_hoy_pct:.1f}% (mejor que mercado)", "💪 OPORTUNIDAD: Fortaleza relativa"
        else:
            return "SISTEMICA", "NEUTRA", f"Mercado {cambio_spy:.1f}%, tu caida {cambio_hoy_pct:.1f}% (alineado)", "🤔 SISTEMICA: Esperar estabilizacion"
    
    # Si mercado tranquilo pero caida fuerte -> idiosincratica
    return "IDIOSINCRATICA", None, f"Mercado tranquilo ({cambio_spy:.1f}%), tu caida {cambio_hoy_pct:.1f}%", "🔍 Analizar noticia especifica"


def clasificar_caida(historial, precio_actual, cambio_hoy_pct):
    """
    Clasifica la caida en: PANICO, SOBREVENTA, o INCERTIDUMBRE.
    Usa volumen como proxy de panico institucional.
    Devuelve: (clasificacion, mensaje)
    """
    try:
        volumen_hoy = historial["Volume"].iloc[-1]
        media_volumen_20 = historial["Volume"].iloc[-21:-1].mean()
        ratio_volumen = volumen_hoy / media_volumen_20 if media_volumen_20 > 0 else 1
    except:
        ratio_volumen = 1
    
    # Caída 15%+ con volumen normal -> sobreventa tecnica (oportunidad)
    if abs(cambio_hoy_pct) >= 15 and ratio_volumen < 1.5:
        return "SOBREVENTA_TECNICA", f"Caida {cambio_hoy_pct:.1f}% con volumen normal (x{ratio_volumen:.1f}) -> Sobreventa exagerada"
    
    # Caída 15%+ con volumen 3x+ -> panico institucional (trampa)
    if abs(cambio_hoy_pct) >= 15 and ratio_volumen > 3:
        return "PANICO_INSTITUCIONAL", f"Caida {cambio_hoy_pct:.1f}% con volumen masivo (x{ratio_volumen:.1f}) -> Panico institucional"
    
    # Caída 15%+ con volumen 1.5-3x -> alta incertidumbre (esperar)
    if abs(cambio_hoy_pct) >= 15:
        return "ALTA_INCERTIDUMBRE", f"Caida {cambio_hoy_pct:.1f}% con volumen elevado (x{ratio_volumen:.1f}) -> Esperar 48h"
    
    # Caída 7-15% con volumen alto -> posible trampa
    if abs(cambio_hoy_pct) >= 7 and ratio_volumen > 2:
        return "ALTA_INCERTIDUMBRE", f"Caida {cambio_hoy_pct:.1f}% con volumen alto (x{ratio_volumen:.1f}) -> Precaucion"
    
    # Caída moderada <7% -> normal
    return "CAIDA_NORMAL", f"Caida {cambio_hoy_pct:.1f}% con volumen x{ratio_volumen:.1f} -> Dentro de rango normal"


def evaluar_caida_para_buyhold(ticker, historial, precio_actual, crec_anual, upside_anal, revenue_growth, score_base, status_base, motivos_base):
    """
    Evalua una caida reciente desde la perspectiva de Buy & Hold 4Y.
    Aplica reglas de disciplina: no comprar el dia de la caida, esperar 48h.
    Devuelve: (score_modificado, status_modificado, motivos_modificados, alertas)
    """
    alertas = []
    score = score_base
    status = status_base
    motivos = motivos_base.copy()
    
    try:
        precio_ayer = historial["Close"].iloc[-2]
        cambio_hoy = ((precio_actual - precio_ayer) / precio_ayer) * 100
    except:
        return score, status, motivos, alertas
    
    # Si no hay caida significativa, no hacer nada
    if cambio_hoy > -5:
        return score, status, motivos, alertas
    
    # Analizar contexto y clasificar
    origen, fortaleza, msg_contexto, recom_contexto = analizar_contexto_caida(ticker, cambio_hoy)
    clasificacion, msg_clasificacion = clasificar_caida(historial, precio_actual, cambio_hoy)
    
    alertas.append(f"📉 Caida hoy: {cambio_hoy:.1f}% | {msg_contexto}")
    alertas.append(f"📊 Clasificacion: {clasificacion} | {msg_clasificacion}")
    
    # REGLAS DE DECISION PARA BUY & HOLD
    
    # 1. PANICO INSTITUCIONAL -> NO COMPRAR, posible vender si ya tienes
    if clasificacion == "PANICO_INSTITUCIONAL":
        score = 0
        status = "🔴 NO COMPRAR"
        motivos.insert(0, f"🚩 PANICO INSTITUCIONAL: {msg_clasificacion}")
        alertas.append("🚫 NO COMPRAR: Esperar 3-5 dias minimo")
        return score, status, motivos, alertas
    
    # 2. ALTA INCERTIDUMBRE -> penalizar, esperar 48h
    if clasificacion == "ALTA_INCERTIDUMBRE":
        score -= 3
        motivos.append(f"⏳ Alta incertidumbre post-caida: {msg_clasificacion}")
        alertas.append("⏳ ESPERAR 48h: No comprar hoy, revisar manana")
        if score < 4 and status == "🟢 COMPRAR":
            status = "🟡 ACUMULAR"
        if score < 4 and status == "🟡 ACUMULAR":
            status = "🔴 OBSERVAR"
        return score, status, motivos, alertas
    
    # 3. SOBREVENTA TECNICA -> oportunidad SOLO si fundamental intacto
    if clasificacion == "SOBREVENTA_TECNICA":
        if revenue_growth and revenue_growth >= 10:
            motivos.append(f"🎯 SOBREVENTA TECNICA en fondamental sano: {msg_clasificacion}")
            alertas.append("✅ OPORTUNIDAD: Caida exagerada, fundamental intacto")
            alertas.append("⚠️ PERO: No comprar hoy. Esperar confirmacion manana")
            # Mantener score pero marcar para revision manana
        else:
            score -= 2
            motivos.append(f"⚠️ Sobreventa pero fondamental debil: {msg_clasificacion}")
            alertas.append("🚫 PRECAUCION: Sin revenue growth fuerte, no es oportunidad clara")
        return score, status, motivos, alertas
    
    # 4. CAIDA SISTEMICA con fortaleza relativa -> oportunidad
    if origen == "SISTEMICA" and fortaleza == "FUERTE":
        motivos.append(f"💪 Fortaleza relativa en caida sistemica: {msg_contexto}")
        alertas.append("✅ OPORTUNIDAD: Caes menos que el mercado, muestra resistencia")
        return score, status, motivos, alertas
    
    # 5. CAIDA SISTEMICA con debilidad relativa -> trampa
    if origen == "SISTEMICA" and fortaleza == "DEBIL":
        score -= 2
        motivos.append(f"🚩 Debilidad relativa en caida sistemica: {msg_contexto}")
        alertas.append("🚫 TRAMPA: Caes mas que el mercado, hay problema especifico")
        if score < 4:
            status = "🔴 OBSERVAR"
        return score, status, motivos, alertas
    
    
    return score, status, motivos, alertas

def calcular_score_y_status(crec_anual, upside_anal, revenue_growth, rsi_valor, media_200, precio_actual):
    """Nuevo scoring v6.1 sobre 10 puntos. Penaliza si Potencial Compuesto < 20%."""
    score = 0
    motivos = []
    
    potencial = calcular_potencial_compuesto(crec_anual, upside_anal, revenue_growth)

    if precio_actual > media_200:
        score += 4
        motivos.append("Tendencia alcista (+4)")
    else:
        motivos.append("Sin tendencia alcista")

    if crec_anual >= 20.0:
        score += 2
        motivos.append(f"Momentum fuerte {crec_anual:.1f}% (+2)")
    elif crec_anual >= 10.0:
        score += 1
        motivos.append(f"Momentum moderado {crec_anual:.1f}% (+1)")
    else:
        motivos.append(f"Momentum debil {crec_anual:.1f}%")

    if upside_anal is not None and upside_anal > 10.0:
        score += 2
        motivos.append(f"Upside analista {upside_anal:.1f}% (+2)")
    elif upside_anal is not None and upside_anal > 0:
        score += 1
        motivos.append(f"Upside analista {upside_anal:.1f}% (+1)")
    else:
        motivos.append("Sin upside analista confirmado")

    if revenue_growth is not None and revenue_growth >= 20.0:
        score += 2
        motivos.append(f"Revenue growth fuerte {revenue_growth:.1f}% (+2)")
    elif revenue_growth is not None and revenue_growth >= 10.0:
        score += 1
        motivos.append(f"Revenue growth moderado {revenue_growth:.1f}% (+1)")
    elif revenue_growth is not None:
        motivos.append(f"Revenue growth debil {revenue_growth:.1f}%")
    else:
        motivos.append("Sin datos de revenue growth")

    if potencial is not None and potencial < 20.0:
        score -= 2
        motivos.append(f"⚠️ Potencial compuesto {potencial:.1f}% < 20% (-2)")

    if rsi_valor > 70:
        score -= 3
        motivos.append(f"RSI {rsi_valor:.0f} sobrecompra (-3)")
    elif rsi_valor > 65:
        score -= 1
        motivos.append(f"RSI {rsi_valor:.0f} elevado (-1)")

    score = max(0, score)

    if score >= 7:
        status = "🟢 COMPRAR"
    elif score >= 4:
        status = "🟡 ACUMULAR"
    else:
        status = "🔴 OBSERVAR"

    return score, status, motivos, potencial

# ============================================================================
# FUNCIONES DE DATOS
# ============================================================================

@st.cache_data(ttl=300)
def obtener_info_segura(ticker):
    try:
        ticker_real = TICKER_ALIASES.get(ticker.upper(), ticker)
        t = yf.Ticker(ticker_real)
        info = t.info
        if not info or len(info) < 5:
            return None, None, detectar_moneda(ticker), None, None, None, None, None
        target = info.get("targetMedianPrice", None)
        dy = info.get("dividendYield", None)
        moneda = info.get("currency", detectar_moneda(ticker))
        pct_inst = info.get("heldPercentInstitutions", None)
        market_cap = info.get("marketCap", None)
        sector = info.get("sector", None)
        beta_info = info.get("beta", None)
        if beta_info is None:
            beta_info = info.get("beta3Year", None)
        if beta_info is None:
            beta_info = info.get("beta5Year", None)
        revenue_growth = info.get("revenueGrowth", None)
        if dy is not None:
            if dy > 1.0:
                dy = dy / 100.0
            if dy > 0.10:
                dy = 0.0
        return target, dy, moneda, pct_inst, market_cap, sector, beta_info, revenue_growth
    except:
        return None, None, detectar_moneda(ticker), None, None, None, None, None

def descargar_datos_seguro(tickers, period="1y", interval=None, actions=False):
    if isinstance(tickers, list):
        tickers_resueltos = [TICKER_ALIASES.get(t.upper(), t) for t in tickers]
        tickers_str = " ".join(tickers_resueltos)
    else:
        tickers_str = TICKER_ALIASES.get(tickers.upper(), tickers)
        tickers = [tickers]
    try:
        kwargs = {"period": period, "progress": False, "group_by": "ticker"}
        if interval:
            kwargs["interval"] = interval
        if actions:
            kwargs["actions"] = True
        datos = yf.download(tickers_str, **kwargs)
        if len(tickers) == 1 and isinstance(datos.columns, pd.Index):
            ticker = tickers[0]
            datos.columns = pd.MultiIndex.from_product([[ticker], datos.columns])
        return datos
    except Exception as e:
        st.error(f"Error descargando datos batch: {e}")
        return pd.DataFrame()

def extraer_historial(datos_globales, ticker, period="1y"):
    try:
        if not datos_globales.empty:
            niveles = datos_globales.columns.get_level_values(0)
            if ticker in niveles:
                historial = datos_globales[ticker].dropna()
                if not historial.empty:
                    return historial
    except:
        pass
    try:
        ticker_real = TICKER_ALIASES.get(ticker.upper(), ticker)
        t = yf.Ticker(ticker_real)
        historial = t.history(period=period, actions=True)
        return historial
    except:
        return pd.DataFrame()

def extraer_precio_actual(datos_minuto, ticker, historial):
    try:
        if not datos_minuto.empty:
            niveles = datos_minuto.columns.get_level_values(0)
            if ticker in niveles:
                precio = datos_minuto[ticker]["Close"].dropna()
                if len(precio) > 0:
                    ultimo = precio.iloc[-1]
                    if pd.notna(ultimo) and float(ultimo) > 0:
                        return float(ultimo)
    except:
        pass
    try:
        if not historial.empty:
            precio = historial["Close"].iloc[-1]
            if pd.notna(precio) and float(precio) > 0:
                return float(precio)
    except:
        pass
    return None

def calcular_dividend_yield(historial, precio_actual, ticker):
    try:
        _, dy, _, _, _, _, _, _ = obtener_info_segura(ticker)
        if dy is not None and dy > 0:
            return dy
    except:
        pass
    try:
        if "Dividends" in historial.columns and precio_actual > 0:
            dividendos_anuales = historial["Dividends"].tail(252).sum()
            if dividendos_anuales > 0:
                dy_calc = dividendos_anuales / precio_actual
                return min(dy_calc, 0.10)
    except:
        pass
    return 0

def formatear_dividendo(dy):
    if dy is None or dy == 0:
        return "❌ 0%"
    return f"💰 {dy * 100:.2f}%"

def formatear_market_cap(mc):
    if mc is None:
        return "N/A"
    if mc >= 1e12:
        return f"{mc/1e12:.2f}T"
    elif mc >= 1e9:
        return f"{mc/1e9:.2f}B"
    elif mc >= 1e6:
        return f"{mc/1e6:.2f}M"
    return f"{mc:.0f}"

def formatear_pnl(ganancia_valor, ganancia_pct, moneda="USD"):
    sym = simbolo_moneda(moneda)
    if ganancia_valor > 0:
        return f"🟩 +{ganancia_valor:.2f} {sym} (+{ganancia_pct:.2f}%)"
    elif ganancia_valor < 0:
        return f"🟥 {ganancia_valor:.2f} {sym} ({ganancia_pct:.2f}%)"
    return f"⬜ 0.00 {sym} (0.00%)"

def calcular_dias_candado(fecha_candado_str):
    try:
        fecha_candado = datetime.strptime(fecha_candado_str.replace("🔒 ", "").strip(), "%d/%m/%Y")
        hoy = datetime.now()
        dias = (fecha_candado - hoy).days
        return dias
    except:
        return -999

def esta_candado_liberado(fecha_candado_str):
    return calcular_dias_candado(fecha_candado_str) <= 0

def generar_veredicto(fila):
    try:
        ticker = str(fila.get("Ticker", "N/A"))
        score = fila.get("Score", 0)
        crec = str(fila.get("Crecimiento Anualizado", "0%"))
        upside = str(fila.get("Upside Analista", "N/A"))
        potencial = str(fila.get("Potencial Compuesto", "N/A"))
        confianza = str(fila.get("Confianza Dato", "N/A"))
        alertas = fila.get("Alertas Caida", "")
        veredictos = []
        if score >= 7:
            veredictos.append("🚀 Score excelente")
        elif score >= 4:
            veredictos.append("📈 Score favorable")
        else:
            veredictos.append("⚠️ Score debil")
        if upside != "N/A" and upside != "0%":
            upside_num = float(upside.replace("%", "").strip()) if "%" in upside else 0
            if upside_num > 20:
                veredictos.append("upside analista fuerte")
            elif upside_num > 10:
                veredictos.append("upside analista moderado")
        if potencial != "N/A":
            pot_num = float(potencial.replace("%", "").strip()) if "%" in potencial else 0
            if pot_num < 20:
                veredictos.append("⚠️ potencial < 20%")
        if "🔴" in confianza or "BAJA" in confianza:
            veredictos.append("🚩 confianza de datos baja")
        if alertas and len(alertas) > 0:
            if "PANICO" in alertas or "TRAMPA" in alertas:
                veredictos.insert(0, "🚨 ALERTA CAIDA")
        return " | ".join(veredictos)
    except Exception as e:
        return f"⚠️ Error: {str(e)[:30]}"


def analizar_cartera_global(df):
    if df.empty:
        return []
    recomendaciones = []
    scores = []
    potenciales = []
    alertas_caida = 0
    for _, fila in df.iterrows():
        try:
            s = float(fila.get("Score", 0)) if pd.notna(fila.get("Score", 0)) else 0
            scores.append(s)
            p = fila.get("Potencial Compuesto", "N/A")
            if p != "N/A":
                potenciales.append(float(p.replace("%", "")))
            alertas = fila.get("Alertas Caida", "")
            if alertas and ("PANICO" in alertas or "TRAMPA" in alertas):
                alertas_caida += 1
        except:
            pass
    score_medio = sum(scores) / len(scores) if scores else 0
    if score_medio >= 7:
        recomendaciones.append(f"✅ **Score medio {score_medio:.1f}/10**: Cartera de alta calidad.")
    elif score_medio >= 4:
        recomendaciones.append(f"⚖️ **Score medio {score_medio:.1f}/10**: Cartera equilibrada.")
    else:
        recomendaciones.append(f"🛡️ **Score medio {score_medio:.1f}/10**: Revisar fundamentales.")
    
    if potenciales:
        pot_medio = sum(potenciales) / len(potenciales)
        if pot_medio < 20:
            recomendaciones.append(f"⚠️ **Potencial medio cartera {pot_medio:.1f}% < 20%** - Revisar seleccion")
        else:
            recomendaciones.append(f"✅ **Potencial medio cartera {pot_medio:.1f}%** - Buen horizonte")
    
    if alertas_caida > 0:
        recomendaciones.append(f"🚨 **{alertas_caida} activos con alerta de caida** - Revisar urgentemente")
    
    candados_proximos = []
    for _, fila in df.iterrows():
        candado = str(fila.get("Candado", ""))
        dias = calcular_dias_candado(candado)
        if 0 < dias <= 14:
            candados_proximos.append(f"{fila['Ticker']} ({dias}d)")
    if candados_proximos:
        recomendaciones.append(f"🔓 **Candados proximos:** {', '.join(candados_proximos)}")
    sectores = set()
    for tick in df["Ticker"].tolist():
        try:
            _, _, _, _, _, sector, _, _ = obtener_info_segura(tick)
            if sector:
                sectores.add(sector)
        except:
            pass
    if len(sectores) >= 3:
        recomendaciones.append(f"🔄 **Diversificacion en {len(sectores)} sectores.**")
    else:
        recomendaciones.append(f"🎯 **Concentrado en pocos sectores:** Alta correlacion.")
    recomendaciones.append("---")
    recomendaciones.append("**💡 Proximos pasos:**")
    recomendaciones.append("• Manten el candado de 90 dias. No tomes decisiones impulsivas.")
    recomendaciones.append("• Revisa esta cartera una vez por semana, no diariamente.")
    return recomendaciones


def detectar_caida_violenta(historial, precio_actual):
    try:
        precio_ayer = historial["Close"].iloc[-2]
        cambio_hoy = ((precio_actual - precio_ayer) / precio_ayer) * 100
        maximo_20d = historial["Close"].iloc[-20:].max()
        caida_vs_max = ((precio_actual - maximo_20d) / maximo_20d) * 100
        volumen_hoy = historial["Volume"].iloc[-1]
        media_volumen_20 = historial["Volume"].iloc[-21:-1].mean()
        ratio_volumen = volumen_hoy / media_volumen_20 if media_volumen_20 > 0 else 1

        if cambio_hoy < -10:
            if ratio_volumen > 2.5:
                return True, f"CAIDA VIOLENTA: {cambio_hoy:.1f}% hoy con volumen x{ratio_volumen:.1f} (panico institucional)", 3
            else:
                return True, f"CAIDA EXTREMA: {cambio_hoy:.1f}% en un dia", 3
        elif cambio_hoy < -7:
            if ratio_volumen > 2.0:
                return True, f"CAIDA FUERTE: {cambio_hoy:.1f}% con volumen x{ratio_volumen:.1f}", 2
            else:
                return True, f"CAIDA FUERTE: {cambio_hoy:.1f}%", 2
        elif cambio_hoy < -5:
            return True, f"CAIDA SIGNIFICATIVA: {cambio_hoy:.1f}%", 1
        if caida_vs_max < -20 and cambio_hoy < -3:
            return True, f"EN CAIDA LIBRE: -{abs(caida_vs_max):.1f}% desde maximo 20d, hoy {cambio_hoy:.1f}%", 2
        minimo_20d = historial["Close"].iloc[-20:].min()
        if precio_actual < minimo_20d * 0.98 and cambio_hoy < -3:
            return True, f"RUPTURA DE SOPORTE: rompio minimo 20d con {cambio_hoy:.1f}%", 2
        return False, "", 0
    except Exception as e:
        return False, "", 0

# ============================================================================
# INICIALIZACION DE SESSION STATE
# ============================================================================

if "listas_guardadas" not in st.session_state:
    listas_persistidas = cargar_listas()
    if listas_persistidas:
        st.session_state.listas_guardadas = listas_persistidas
    else:
        st.session_state.listas_guardadas = LISTAS_DEFINITIVAS.copy()

if "cartera_compras" not in st.session_state:
    st.session_state.cartera_compras = cargar_cartera()

PARAMS_DEFAULT = {
    "capital_total": 30000,
    "max_por_accion": 1000,
    "tope_semanal": 5000,
    "max_compras_semanal": 5,
    "max_activos_cartera": 10,
    "dias_candado": 90,
    "umbral_sustitucion": 1.5
}

if "params_bot" not in st.session_state:
    st.session_state.params_bot = PARAMS_DEFAULT.copy()
else:
    for key, val in PARAMS_DEFAULT.items():
        if key not in st.session_state.params_bot:
            st.session_state.params_bot[key] = val

if "registro_semanal" not in st.session_state:
    st.session_state.registro_semanal = cargar_registro()

if "propuesta_sustitucion" not in st.session_state:
    st.session_state.propuesta_sustitucion = None

semana_actual = datetime.now().strftime("%Y-W%U")
if semana_actual not in st.session_state.registro_semanal:
    st.session_state.registro_semanal[semana_actual] = {
        "compras_realizadas": 0,
        "gastado": 0.0,
        "tickers_comprados": []
    }

def get_registro_semana_actual():
    semana = datetime.now().strftime("%Y-W%U")
    if semana not in st.session_state.registro_semanal:
        st.session_state.registro_semanal[semana] = {
            "compras_realizadas": 0,
            "gastado": 0.0,
            "tickers_comprados": []
        }
    return st.session_state.registro_semanal[semana]

def puede_comprar_esta_semana(cantidad=1, costo=1000):
    datos = get_registro_semana_actual()
    tope = st.session_state.params_bot["tope_semanal"]
    max_compras = st.session_state.params_bot["max_compras_semanal"]
    if datos["gastado"] + costo > tope:
        return False, f"Tope semanal: {datos["gastado"]:.0f}/{tope}"
    if datos["compras_realizadas"] + cantidad > max_compras:
        return False, f"Max {max_compras} compras: {datos["compras_realizadas"]}/{max_compras}"
    return True, "OK"

def registrar_compra(ticker, costo=1000):
    datos = get_registro_semana_actual()
    datos["compras_realizadas"] += 1
    datos["gastado"] += costo
    datos["tickers_comprados"].append(ticker)
    guardar_registro(st.session_state.registro_semanal)

# ============================================================================
# MENU DE PESTANAS
# ============================================================================
pestaña1, pestaña2, pestaña3 = st.tabs([
    "🤖 Bot Masivo Automatico 30k", 
    "🔍 Analizador Tecnico Avanzado", 
    "⚙️ Configuracion de Listas Pregrabadas"
])

# ============================================================================
# PESTANA 1: BOT MASIVO AUTOMATICO 30K
# ============================================================================
with pestaña1:
    st.subheader("🤖 Algoritmo de Seleccion Inteligente - Horizonte 4 Años")

    mercado_activo = comprobar_mercado_abierto()
    if mercado_activo:
        st.success("🟢 MERCADO ABIERTO")
    else:
        st.info("🕒 MERCADO CERRADO: Analisis con ultimos datos disponibles.")

    st.write("#### 🛡️ Reglas de Gestion Monetaria")
    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    with col_r1:
        max_por_accion = st.number_input(
            "Capital por operacion:", min_value=100, max_value=5000, 
            value=st.session_state.params_bot["max_por_accion"], step=100, key="input_max"
        )
        st.session_state.params_bot["max_por_accion"] = max_por_accion
    with col_r2:
        tope_semanal = st.slider(
            "Tope semanal:", min_value=1000, max_value=30000, 
            value=st.session_state.params_bot["tope_semanal"], step=1000, key="slider_tope"
        )
        st.session_state.params_bot["tope_semanal"] = tope_semanal
    with col_r3:
        max_activos = st.number_input(
            "Max. activos:", min_value=1, max_value=30, 
            value=st.session_state.params_bot["max_activos_cartera"], step=1, key="input_max_act"
        )
        st.session_state.params_bot["max_activos_cartera"] = max_activos
    with col_r4:
        max_compras_sem = st.number_input(
            "Max. compras/semana:", min_value=1, max_value=10,
            value=st.session_state.params_bot["max_compras_semanal"], step=1, key="input_max_comp"
        )
        st.session_state.params_bot["max_compras_semanal"] = max_compras_sem

    opciones_lista = ["🌍 TODAS LAS LISTAS"] + list(st.session_state.listas_guardadas.keys())
    lista_bot = st.selectbox(
        "Universo a analizar:",
        opciones_lista,
        key="select_lista_bot"
    )

    col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns([2, 1, 1, 1, 1])
    with col_btn1:
        ejecutar_bot = st.button("🔄 Ejecutar Bot")

    # ============================================================================
    # EJECUCION DEL BOT
    # ============================================================================
    if ejecutar_bot:
        # Obtener tickers a analizar
        if lista_bot == "🌍 TODAS LAS LISTAS":
            tickers_a_analizar = []
            for lista in st.session_state.listas_guardadas.values():
                for t in lista:
                    if t not in tickers_a_analizar:
                        tickers_a_analizar.append(t)
        else:
            tickers_a_analizar = st.session_state.listas_guardadas.get(lista_bot, [])

        if not tickers_a_analizar:
            st.warning("No hay tickers para analizar. Selecciona una lista.")
        else:
            st.info(f"📊 Analizando {len(tickers_a_analizar)} activos...")

            with st.spinner("🚴‍♂️ Descargando datos del mercado..."):
                datos_globales = descargar_datos_seguro(tickers_a_analizar, period="1y", actions=True)

            if datos_globales.empty:
                st.error("❌ No se pudieron descargar datos. Intenta más tarde.")
            else:
                resultados = []
                barra = st.progress(0)
                total = len(tickers_a_analizar)

                for idx, tick in enumerate(tickers_a_analizar):
                    barra.progress(int((idx / total) * 100))
                    try:
                        h = extraer_historial(datos_globales, tick)
                        if h.empty or len(h) < 50:
                            continue

                        p_actual = h["Close"].iloc[-1]
                        if p_actual <= 0:
                            continue

                        media_50 = h["Close"].iloc[-50:].mean()
                        media_200 = h["Close"].iloc[-200:].mean() if len(h) >= 200 else media_50

                        target_val, div_yield, moneda, pct_inst, market_cap, sector, beta_info, revenue_growth = obtener_info_segura(tick)

                        rsi_valor = calcular_rsi(h)
                        beta_valor = calcular_beta(h, beta_info)

                        # Motor v6.1
                        crec_anual, upside_anal, rev_growth = calcular_metricas_limpias(h, p_actual, tick)
                        confianza, motivo_conf = calcular_confianza_dato(crec_anual, upside_anal, rev_growth)
                        potencial_comp = calcular_potencial_compuesto(crec_anual, upside_anal, rev_growth)

                        score, status, motivos, potencial_final = calcular_score_y_status(
                            crec_anual, upside_anal, rev_growth, rsi_valor, media_200, p_actual
                        )

                        # Evaluar caida
                        alertas_caida_list = []
                        try:
                            precio_ayer = h["Close"].iloc[-2]
                            cambio_hoy = ((p_actual - precio_ayer) / precio_ayer) * 100
                            if cambio_hoy <= -5:
                                score, status, motivos, alertas_caida_list = evaluar_caida_para_buyhold(
                                    tick, h, p_actual, crec_anual, upside_anal, rev_growth,
                                    score, status, motivos
                                )
                        except:
                            pass

                        # Alerta caida violenta
                        alerta_caida = None
                        es_peligroso, motivo_caida, severidad = detectar_caida_violenta(h, p_actual)
                        if es_peligroso and severidad >= 2:
                            alerta_caida = motivo_caida
                            status = "🔴 NO COMPRAR"
                            score = 0

                        sym = simbolo_moneda(moneda)

                        confianza_fmt = confianza
                        if confianza == "BAJA":
                            confianza_fmt = "🔴 BAJA"
                        elif confianza == "MEDIA":
                            confianza_fmt = "🟡 MEDIA"
                        else:
                            confianza_fmt = "🟢 ALTA"

                        alertas_str = " | ".join(alertas_caida_list) if alertas_caida_list else ""

                        resultados.append({
                            "Ticker": tick,
                            "Score": score,
                            "Status": status,
                            "Precio": f"{p_actual:.2f} {sym}",
                            "Crecimiento Anualizado": f"{crec_anual:.1f}%",
                            "Upside Analista": f"{upside_anal:.1f}%" if upside_anal else "N/A",
                            "Revenue Growth": f"{rev_growth:.1f}%" if rev_growth else "N/A",
                            "Potencial Compuesto": f"{potencial_comp:.1f}%" if potencial_comp else "N/A",
                            "Confianza Dato": confianza_fmt,
                            "Alertas Caida": alertas_str,
                            "RSI": f"{rsi_valor:.1f}",
                            "Beta": f"{beta_valor:.2f}" if beta_valor else "N/A",
                            "Alerta Volatilidad": "⚠️ BETA ALTO" if beta_valor and beta_valor > 2.0 else "⚡ Volatil" if beta_valor and beta_valor > 1.5 else "",
                            "Volumen H.F.": "N/A",
                            "Dividendo": formatear_dividendo(div_yield),
                            "Interes Inst.": "🎯 FUERTE" if pct_inst and pct_inst > 0.5 else "🎯 MODERADO" if pct_inst else "🎯 DEBIL",
                            "Pct Institucional": f"{pct_inst*100:.1f}%" if pct_inst else "N/A",
                            "Market Cap": formatear_market_cap(market_cap),
                            "Sector": sector or "N/A",
                            "Moneda": moneda,
                            "Motivos": " | ".join(motivos) if motivos else "Sin fortalezas"
                        })
                    except Exception as e:
                        pass

                barra.empty()

                if resultados:
                    df_resultados = pd.DataFrame(resultados)
                    df_resultados = df_resultados.sort_values("Score", ascending=False).reset_index(drop=True)

                    st.write("### 🏆 Resultados del Análisis")
                    st.dataframe(df_resultados, use_container_width=True)

                    # Top oportunidades
                    top = df_resultados[df_resultados["Score"] >= 7].head(5)
                    if not top.empty:
                        st.write("### 🎯 Top Oportunidades (Score ≥ 7)")
                        st.dataframe(top[["Ticker", "Score", "Precio", "Crecimiento Anualizado", 
                                         "Upside Analista", "Dividendo"]], use_container_width=True)

                    # Propuestas de compra
                    cartera_actual = st.session_state.cartera_compras
                    if not isinstance(cartera_actual, pd.DataFrame):
                        cartera_actual = pd.DataFrame()

                    en_cartera = set(cartera_actual["Ticker"].tolist()) if not cartera_actual.empty else set()
                    disponibles = [r for r in resultados if r["Ticker"] not in en_cartera and r["Score"] >= 7]

                    if disponibles and len(cartera_actual) < max_activos:
                        st.write("### 💰 Propuestas de Compra")
                        puede_comprar, msg = puede_comprar_esta_semana(len(disponibles[:max_compras_sem]))
                        if puede_comprar:
                            for r in disponibles[:max_compras_sem]:
                                st.success(f"🟢 {r['Ticker']}: Score {r['Score']}/10 | {r['Precio']} | "
                                          f"Momentum: {r['Crecimiento Anualizado']} | Upside: {r['Upside Analista']}")
                        else:
                            st.info(f"⏳ {msg}")
                    elif len(cartera_actual) >= max_activos:
                        st.info(f"📊 Cartera llena: {len(cartera_actual)}/{max_activos} posiciones")

                        # Sugerir sustitución
                        top_no_cartera = [r for r in resultados if r["Ticker"] not in en_cartera and r["Score"] >= 7][:2]
                        if top_no_cartera:
                            st.write("**Sustituciones sugeridas:**")
                            # Encontrar la peor posición actual
                            peor_score = 999
                            peor_ticker = None
                            for t in en_cartera:
                                row_t = df_resultados[df_resultados["Ticker"] == t]
                                if not row_t.empty:
                                    s = row_t["Score"].iloc[0]
                                    if s < peor_score:
                                        peor_score = s
                                        peor_ticker = t

                            for nuevo in top_no_cartera:
                                if peor_ticker and nuevo["Score"] > peor_score:
                                    st.write(f"🔄 Vender {peor_ticker} (Score {peor_score}) → Comprar {nuevo['Ticker']} (Score {nuevo['Score']})")
                    else:
                        st.info("Todas las top oportunidades ya están en cartera")
                else:
                    st.warning("No se pudieron analizar activos. Verifica la conexión.")

    with col_btn2:
        if st.button("🗑️ Resetear Cartera"):
            st.session_state.cartera_compras = pd.DataFrame()
            st.session_state.registro_semanal = {}
            st.cache_data.clear()
            if os.path.exists(CARTERA_FILE):
                os.remove(CARTERA_FILE)
            if os.path.exists(REGISTRO_FILE):
                os.remove(REGISTRO_FILE)
            st.success("¡Cartera y registro reseteados!")
            time.sleep(1)
            st.rerun()
    with col_btn3:
        if st.button("🧹 Limpiar Duplicados"):
            if not st.session_state.cartera_compras.empty:
                antes = len(st.session_state.cartera_compras)
                st.session_state.cartera_compras = st.session_state.cartera_compras.drop_duplicates(
                    subset=["Ticker"], keep="last"
                ).reset_index(drop=True)
                guardar_cartera(st.session_state.cartera_compras)
                st.success(f"Eliminados {antes - len(st.session_state.cartera_compras)} duplicados.")
                st.rerun()
    with col_btn4:
        if not st.session_state.cartera_compras.empty:
            csv_cartera = st.session_state.cartera_compras.to_csv(index=False)
            st.download_button(
                label="📥 Exportar", data=csv_cartera,
                file_name="cartera_guardada.csv", mime="text/csv",
                key="export_cartera"
            )
        else:
            st.button("📥 Exportar", disabled=True, key="export_cartera_disabled")
    with col_btn5:
        archivo_cartera = st.file_uploader("📤 Importar CSV", type=["csv"], key="import_cartera", label_visibility="collapsed")
        if archivo_cartera is not None:
            try:
                df_import = pd.read_csv(archivo_cartera)
                if not df_import.empty:
                    st.session_state.cartera_compras = df_import
                    guardar_cartera(st.session_state.cartera_compras)
                    st.success(f"✅ Cartera importada: {len(df_import)} posiciones")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")

    # MOSTRAR CARTERA
    df_mostrar = st.session_state.cartera_compras.copy()
    capital_total = st.session_state.params_bot["capital_total"]
    caja_libre = capital_total
    gastado_semana = 0.0
    alerta_cupo = False

    if not df_mostrar.empty:
        invertido_total = df_mostrar["Capital Invertido Base"].sum()
        caja_libre = capital_total - invertido_total
        gastado_semana = get_registro_semana_actual()["gastado"]
        alerta_cupo = len(df_mostrar) >= max_activos

        lista_activos = df_mostrar["Ticker"].tolist()
        precios_vivos = {}

        with st.spinner("🔄 Actualizando precios..."):
            try:
                cotizaciones_batch = yf.download(" ".join(lista_activos), period="5d", interval="1d", group_by="ticker", progress=False)
                if len(lista_activos) == 1:
                    precios_vivos[lista_activos[0]] = float(cotizaciones_batch["Close"].iloc[-1])
                else:
                    for tick in lista_activos:
                        if tick in cotizaciones_batch.columns.levels[0]:
                            precios_vivos[tick] = float(cotizaciones_batch[tick]["Close"].iloc[-1])
            except:
                pass

        lista_pnl = []
        for _, fila in df_mostrar.iterrows():
            t = fila["Ticker"]
            p_entrada = fila["Precio Entrada Base"]
            n = fila["Acciones"]
            moneda = fila.get("Moneda", "USD")
            p_live = precios_vivos.get(t, p_entrada)
            ganancia_valor = (p_live - p_entrada) * n
            ganancia_pct = ((p_live - p_entrada) / p_entrada) * 100 if p_entrada > 0 else 0
            lista_pnl.append(formatear_pnl(ganancia_valor, ganancia_pct, moneda))

        df_mostrar["Rendimiento Actual (P&L)"] = lista_pnl

        try:
            df_mostrar["📝 Veredicto"] = df_mostrar.apply(generar_veredicto, axis=1)
        except:
            df_mostrar["📝 Veredicto"] = "⚠️ Pendiente"

        df_mostrar["Estado Candado"] = df_mostrar["Candado"].apply(
            lambda x: "🔓 LIBERADO" if esta_candado_liberado(x) else x
        )

    total_invertido = capital_total - caja_libre

    st.write("---")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Capital Total", f"{capital_total:,.0f}")
    c2.metric("Invertido", f"{total_invertido:,.2f}")
    c3.metric("Caja Libre", f"{caja_libre:,.2f}")
    c4.metric("Semanal", f"{gastado_semana:,.0f}/{tope_semanal:,.0f}")
    c5.metric("Compras Sem", f"{get_registro_semana_actual()['compras_realizadas']}/{max_compras_sem}")

    if alerta_cupo:
        st.warning(f"⚠️ Cupo maximo {max_activos} alcanzado.")

    st.write("---")
    st.write("### 📊 Cartera a 4 Años")
    if not df_mostrar.empty:
        cols = ["Ticker", "Acciones", "Precio Entrada", "Rendimiento Actual (P&L)", 
                "Crecimiento Anualizado", "Upside Analista", "Revenue Growth", 
                "Potencial Compuesto", "Confianza Dato", "Alertas Caida", "Score",
                "RSI", "Beta", "Alerta Volatilidad", "Volumen H.F.", 
                "Dividendo", "Interes Inst.", "Market Cap",
                "📝 Veredicto", "Estado Candado", "Capital Invertido", "Fecha Compra"]
        cols_existentes = [c for c in cols if c in df_mostrar.columns]
        st.dataframe(df_mostrar[cols_existentes], use_container_width=True)
    else:
        st.info("Cartera vacia. Ejecuta el bot.")

    # ============================================================================
    # PROPUESTAS DE SUSTITUCION (HUMAN-IN-THE-LOOP)
    # ============================================================================
    if st.session_state.propuesta_sustitucion is not None:
        st.write("---")
        st.write("### 🔀 Propuesta de Sustitucion Pendiente")

        prop = st.session_state.propuesta_sustitucion

        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.error(f"🗑️ VENDER: **{prop['vender']}**")
            st.write(f"Score actual: {prop['score_viejo']:.0f}/10")
        with col_info2:
            st.success(f"💰 COMPRAR: **{prop['comprar']}**")
            st.write(f"Score: {prop['score_nuevo']}/10")
            st.write(f"Upside Analista: {prop['upside_nuevo']}")
            st.write(f"Precio: {prop['precio_nuevo']:.2f} {prop['moneda_nuevo']}")

        st.write("**Motivos de la propuesta:**")
        st.write(f"• La nueva oportunidad tiene un Score {prop['score_nuevo']/prop['score_viejo']:.1f}x mejor")
        st.write(f"• El activo actual ({prop['vender']}) tiene el candado liberado")

        col_ok, col_ko = st.columns(2)
        with col_ok:
            if st.button("✅ AUTORIZAR SUSTITUCION", key="auth_sustitucion"):
                fila = pd.Series(prop["fila_completa"])

                cartera_actual = st.session_state.cartera_compras
                idx_vender = cartera_actual[cartera_actual["Ticker"] == prop["vender"]].index[0]
                capital_liberado = cartera_actual.loc[idx_vender, "Capital Invertido Base"]

                cartera_actual = cartera_actual.drop(idx_vender).reset_index(drop=True)
                st.session_state.cartera_compras = cartera_actual

                fecha_compra = datetime.now().strftime("%d/%m/%Y")
                fecha_liberacion = (datetime.now() + timedelta(days=st.session_state.params_bot["dias_candado"])).strftime("%d/%m/%Y")
                precio = prop["precio_nuevo"]
                cantidad = round(max_por_accion / precio, 4)

                nueva_posicion = {
                    "Ticker": prop["comprar"],
                    "Acciones": cantidad,
                    "Precio Entrada Base": precio,
                    "Precio Entrada": f"{precio:.2f} {prop['moneda_nuevo']}",
                    "Crecimiento Anualizado": f"{fila['Crecimiento Anualizado']:.1f}%",
                    "Upside Analista": fila["Upside Analista"],
                    "Revenue Growth": fila["Revenue Growth"],
                    "Potencial Compuesto": fila["Potencial Compuesto"],
                    "Confianza Dato": fila["Confianza Dato"],
                    "Alertas Caida": fila["Alertas Caida"],
                    "Score": fila["Score"],
                    "RSI": fila["RSI"],
                    "Beta": fila["Beta"],
                    "Alerta Volatilidad": fila["Alerta Volatilidad"],
                    "Volumen H.F.": fila["Volumen H.F."],
                    "Dividendo": formatear_dividendo(fila["Dividendo"]),
                    "Interes Inst.": "🎯 FUERTE" if fila["Pct Institucional"] and fila["Pct Institucional"] > 0.5 else "🎯 MODERADO" if fila["Pct Institucional"] else "🎯 DEBIL",
                    "Pct Institucional": f"{fila['Pct Institucional']*100:.1f}%" if fila['Pct Institucional'] else "N/A",
                    "Market Cap": formatear_market_cap(fila["Market Cap"]),
                    "Capital Invertido Base": max_por_accion,
                    "Capital Invertido": f"{max_por_accion:.2f} {prop['moneda_nuevo']}",
                    "Fecha Compra": fecha_compra,
                    "Candado": f"🔒 {fecha_liberacion}",
                    "Moneda": fila["Moneda"]
                }

                df_nueva = pd.DataFrame([nueva_posicion])
                st.session_state.cartera_compras = pd.concat([cartera_actual, df_nueva], ignore_index=True)
                guardar_cartera(st.session_state.cartera_compras)
                registrar_compra(prop["comprar"], max_por_accion)

                st.session_state.propuesta_sustitucion = None
                st.success(f"✅ Sustitucion ejecutada: {prop['vender']} → {prop['comprar']}")
                st.rerun()

        with col_ko:
            if st.button("❌ RECHAZAR SUSTITUCION", key="reject_sustitucion"):
                st.session_state.propuesta_sustitucion = None
                st.info("❌ Sustitucion rechazada. La propuesta se ha descartado.")
                st.rerun()

    if not df_mostrar.empty:
        st.write("---")
        st.write("### 🧠 Analisis de tu Cartera")
        try:
            for rec in analizar_cartera_global(df_mostrar):
                st.write(rec)
        except Exception as e:
            st.error(f"⚠️ Error: {e}")
        st.info("📅 Revisa una vez por semana. No tomes decisiones impulsivas.")

# ============================================================================
# PESTANA 2: ANALIZADOR TECNICO
# ============================================================================
with pestaña2:
    st.subheader("🔍 Analizador de Oportunidades - Horizonte 4 Años")

    st.write("### 📈 Analisis Individual")
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        ticker_individual = st.text_input("Ticker:", value="", placeholder="Ej: NVDA, AMD, ARM...", key="ticker_individual")
    with col_btn:
        analizar_individual = st.button("🔍 Analizar", key="btn_analizar_individual")

    if analizar_individual and ticker_individual.strip():
        tick = ticker_individual.strip().upper()
        with st.spinner(f"Analizando {tick}..."):
            try:
                ticker_real = TICKER_ALIASES.get(tick, tick)
                h = yf.Ticker(ticker_real).history(period="1y")
                if h.empty or len(h) < 50:
                    st.error(f"No hay suficientes datos para {tick}")
                else:
                    p_actual = h["Close"].iloc[-1]
                    media_50 = h["Close"].iloc[-50:].mean()
                    media_200 = h["Close"].iloc[-200:].mean() if len(h) >= 200 else media_50

                    target_val, div_yield, moneda, pct_inst, market_cap, sector, beta_info, revenue_growth = obtener_info_segura(tick)

                    rsi_valor = calcular_rsi(h)
                    beta_valor = calcular_beta(h, beta_info)

                    # NUEVO MOTOR v6.1
                    crec_anual, upside_anal, rev_growth = calcular_metricas_limpias(h, p_actual, tick)
                    
                    confianza, motivo_conf = calcular_confianza_dato(crec_anual, upside_anal, rev_growth)
                    potencial_comp = calcular_potencial_compuesto(crec_anual, upside_anal, rev_growth)
                    
                    score, status, motivos, potencial_final = calcular_score_y_status(
                        crec_anual, upside_anal, rev_growth, rsi_valor, media_200, p_actual
                    )

                    # NUEVO v6.1: Evaluar contexto de caida
                    alertas_caida_list = []
                    try:
                        precio_ayer = h["Close"].iloc[-2]
                        cambio_hoy = ((p_actual - precio_ayer) / precio_ayer) * 100
                        if cambio_hoy <= -5:
                            score, status, motivos, alertas_caida_list = evaluar_caida_para_buyhold(
                                tick, h, p_actual, crec_anual, upside_anal, rev_growth,
                                score, status, motivos
                            )
                    except:
                        pass

                    # Alerta caida
                    alerta_caida = None
                    es_peligroso, motivo_caida, severidad = detectar_caida_violenta(h, p_actual)
                    if es_peligroso and severidad >= 2:
                        alerta_caida = motivo_caida
                        status = "🔴 NO COMPRAR"
                        score = 0

                    sym = simbolo_moneda(moneda)
                    
                    confianza_fmt = confianza
                    if confianza == "BAJA":
                        confianza_fmt = "🔴 BAJA"
                    elif confianza == "MEDIA":
                        confianza_fmt = "🟡 MEDIA"
                    else:
                        confianza_fmt = "🟢 ALTA"

                    st.write("#### 📊 Evolucion del Precio")
                    h["MA50"] = h["Close"].rolling(window=50).mean()
                    h["MA200"] = h["Close"].rolling(window=200).mean()
                    chart_data = pd.DataFrame({
                        "Precio": h["Close"],
                        "Media 50d": h["MA50"],
                        "Media 200d": h["MA200"]
                    })
                    st.line_chart(chart_data, use_container_width=True)

                    st.write("#### 📋 Metricas Clave")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Precio Actual", f"{p_actual:.2f} {sym}")
                    c2.metric("Crecimiento Anualizado", f"{crec_anual:.1f}%")
                    c3.metric("Upside Analista", f"{upside_anal:.1f}%" if upside_anal else "N/A")
                    c4.metric("Score", f"{score}/10")

                    c5, c6, c7, c8 = st.columns(4)
                    c5.metric("Media 50d", f"{media_50:.2f} {sym}")
                    c6.metric("Media 200d", f"{media_200:.2f} {sym}")
                    c7.metric("Dividendo", formatear_dividendo(div_yield))
                    c8.metric("RSI (14)", f"{rsi_valor:.1f}")
                    
                    c9, c10, c11 = st.columns(3)
                    c9.metric("Revenue Growth", f"{rev_growth:.1f}%" if rev_growth else "N/A")
                    c10.metric("Potencial Compuesto", f"{potencial_comp:.1f}%" if potencial_comp else "N/A")
                    c11.metric("Confianza Dato", confianza_fmt)

                    if alertas_caida_list:
                        st.write("#### 🚨 Alertas de Caida")
                        for alerta in alertas_caida_list:
                            st.warning(alerta)

                    if beta_valor is not None:
                        c_beta = st.columns([1, 2, 1])[1]
                        with c_beta:
                            if beta_valor > 2.0:
                                st.error(f"**Beta: {beta_valor:.2f}** ⚠️ BETA ALTO")
                            elif beta_valor > 1.5:
                                st.warning(f"**Beta: {beta_valor:.2f}** ⚡ Volatil")
                            else:
                                st.info(f"**Beta: {beta_valor:.2f}** ✅ Normal")

                    col_sem = st.columns([1, 2, 1])[1]
                    with col_sem:
                        if alerta_caida:
                            st.error(f"## 🚨 {alerta_caida}")
                            st.error("## 🔴 NO COMPRAR / PELIGRO")
                        elif score >= 7:
                            st.success("## 🟢 COMPRA FUERTE")
                        elif score >= 4:
                            st.warning("## 🟡 COMPRA MODERADA")
                        else:
                            st.error("## 🔴 NO COMPRAR / ESPERAR")
                        st.write(f"**Score: {score}/10**")
                        motivos_display = [f"🚨 {alerta_caida}"] + motivos if alerta_caida else motivos
                        st.write(f"**Motivos:** {', '.join(motivos_display) if motivos_display else 'Sin fortalezas'}")

                    with st.expander("📋 Detalle de puntuacion"):
                        st.write("**Puntuacion (sobre 10):**")
                        st.write(f"• Tendencia (MA200): {'+4' if p_actual > media_200 else '0'}")
                        st.write(f"• Momentum (Crec. Anual): {'+2' if crec_anual >= 20 else '+1' if crec_anual >= 10 else '0'}")
                        st.write(f"• Valor (Upside Analista): {'+2' if upside_anal and upside_anal > 10 else '+1' if upside_anal and upside_anal > 0 else '0'}")
                        st.write(f"• Fundamental (Revenue Growth): {'+2' if rev_growth and rev_growth >= 20 else '+1' if rev_growth and rev_growth >= 10 else '0'}")
                        st.write(f"• Potencial Compuesto: {'-2' if potencial_comp and potencial_comp < 20 else '0'}")
                        st.write(f"• RSI: {'-3' if rsi_valor > 70 else '-1' if rsi_valor > 65 else '0'}")
            except Exception as e:
                st.error(f"Error: {e}")

    st.write("---")
    st.write("### 📋 Analisis de Listas Pregrabadas")
    opciones_lista2 = ["Ninguna", "🌍 TODAS LAS LISTAS"] + list(st.session_state.listas_guardadas.keys())
    lista_sel = st.selectbox("Universo:", opciones_lista2, key="select_lista")

    if lista_sel != "Ninguna":
        if lista_sel == "🌍 TODAS LAS LISTAS":
            tickers_lista = []
            for lista in st.session_state.listas_guardadas.values():
                for t in lista:
                    if t not in tickers_lista:
                        tickers_lista.append(t)
            st.info(f"🌍 Analizando {len(tickers_lista)} tickers de todas las listas")
        else:
            tickers_lista = st.session_state.listas_guardadas[lista_sel]
        if tickers_lista:
            with st.spinner("Analizando..."):
                datos_globales_p2 = descargar_datos_seguro(tickers_lista, period="1y", actions=True)
                datos_lista = []

                barra = st.progress(0)
                tickers_unicos = list(dict.fromkeys(tickers_lista))
                total = len(tickers_unicos)

                for idx, tick in enumerate(tickers_unicos):
                    barra.progress(int((idx / total) * 100))
                    try:
                        h = extraer_historial(datos_globales_p2, tick)
                        if h.empty or len(h) < 50:
                            datos_lista.append({
                                "Ticker": tick, "Status": "⚪ SIN DATOS", "Score": 0,
                                "Precio": "N/A", "Crecimiento Anualizado": "N/A",
                                "Upside Analista": "N/A", "Revenue Growth": "N/A",
                                "Potencial Compuesto": "N/A", "Confianza Dato": "N/A",
                                "Alertas Caida": "", "RSI": "N/A", "Beta": "N/A", "Alerta Volatilidad": "",
                                "Motivo": "Datos insuficientes"
                            })
                            continue

                        p_actual = h["Close"].iloc[-1]
                        p_media = h["Close"].iloc[-50:].mean()

                        target_val, div_yield, moneda, pct_inst, market_cap, sector, beta_info, revenue_growth = obtener_info_segura(tick)

                        rsi_valor = calcular_rsi(h)
                        beta_valor = calcular_beta(h, beta_info)

                        # NUEVO MOTOR v6.1
                        crec_anual, upside_anal, rev_growth = calcular_metricas_limpias(h, p_actual, tick)
                        
                        confianza, motivo_conf = calcular_confianza_dato(crec_anual, upside_anal, rev_growth)
                        potencial_comp = calcular_potencial_compuesto(crec_anual, upside_anal, rev_growth)
                        
                        score, status, motivos, potencial_final = calcular_score_y_status(
                            crec_anual, upside_anal, rev_growth, rsi_valor, p_media, p_actual
                        )

                        # NUEVO v6.1: Evaluar contexto de caida
                        alertas_caida_list = []
                        try:
                            precio_ayer = h["Close"].iloc[-2]
                            cambio_hoy = ((p_actual - precio_ayer) / precio_ayer) * 100
                            if cambio_hoy <= -5:
                                score, status, motivos, alertas_caida_list = evaluar_caida_para_buyhold(
                                    tick, h, p_actual, crec_anual, upside_anal, rev_growth,
                                    score, status, motivos
                                )
                        except:
                            pass

                        # Alerta caida
                        alerta_caida = None
                        es_peligroso, motivo_caida, severidad = detectar_caida_violenta(h, p_actual)
                        if es_peligroso and severidad >= 2:
                            alerta_caida = motivo_caida
                            status = "🔴 NO COMPRAR"
                            score = 0
                            motivos.insert(0, f"🚨 {motivo_caida}")

                        sym = simbolo_moneda(moneda)
                        
                        confianza_fmt = confianza
                        if confianza == "BAJA":
                            confianza_fmt = "🔴 BAJA"
                        elif confianza == "MEDIA":
                            confianza_fmt = "🟡 MEDIA"
                        else:
                            confianza_fmt = "🟢 ALTA"
                        
                        alertas_str = " | ".join(alertas_caida_list) if alertas_caida_list else ""

                        datos_lista.append({
                            "Ticker": tick, 
                            "Status": status, 
                            "Score": score,
                            "Precio": f"{p_actual:.2f} {sym}",
                            "Crecimiento Anualizado": f"{crec_anual:.1f}%",
                            "Upside Analista": f"{upside_anal:.1f}%" if upside_anal else "N/A",
                            "Revenue Growth": f"{rev_growth:.1f}%" if rev_growth else "N/A",
                            "Potencial Compuesto": f"{potencial_comp:.1f}%" if potencial_comp else "N/A",
                            "Confianza Dato": confianza_fmt,
                            "Alertas Caida": alertas_str,
                            "RSI": f"{rsi_valor:.1f}",
                            "Beta": f"{beta_valor:.2f}" if beta_valor is not None else "N/A",
                            "Alerta Volatilidad": "⚠️ BETA ALTO" if beta_valor and beta_valor > 2.0 else "⚡ Volatil" if beta_valor and beta_valor > 1.5 else "",
                            "Motivo": "; ".join(motivos) if motivos else "Sin fortalezas"
                        })
                    except Exception as e:
                        datos_lista.append({
                            "Ticker": tick, "Status": "⚪ ERROR", "Score": 0,
                            "Precio": "N/A", "Crecimiento Anualizado": "N/A",
                            "Upside Analista": "N/A", "Revenue Growth": "N/A",
                            "Potencial Compuesto": "N/A", "Confianza Dato": "N/A",
                            "Alertas Caida": "", "RSI": "N/A", "Beta": "N/A", "Alerta Volatilidad": "",
                            "Motivo": f"Error: {str(e)[:30]}"
                        })

                barra.empty()

                if datos_lista:
                    df_lista = pd.DataFrame(datos_lista)
                    df_lista = df_lista.sort_values(by="Score", ascending=False)
                    st.write(f"**{len(df_lista)} activos analizados**")

                    # Destacar cuales compraria el bot
                    df_comprar = df_lista[df_lista["Status"].isin(["🟢 COMPRAR", "🟡 ACUMULAR"])]
                    if not df_comprar.empty:
                        st.success(f"🟢 El Bot compraria: {', '.join(df_comprar["Ticker"].tolist())}")

                    st.dataframe(df_lista, use_container_width=True)
                else:
                    st.warning("No se pudieron analizar activos.")
        else:
            st.info("Lista vacia.")

# ============================================================================
# PESTANA 3: CONFIGURACION DE LISTAS
# ============================================================================
with pestaña3:
    st.subheader("⚙️ Gestion de Listas de Seguimiento")

    for nombre_lista, tickers_lista in st.session_state.listas_guardadas.items():
        with st.expander(f"📋 {nombre_lista} ({len(tickers_lista)} tickers)"):
            st.write(f"**Tickers:** {', '.join(tickers_lista)}")

            st.write("**✏️ Editar tickers:**")

            col_del_sel, col_del_btn = st.columns([3, 1])
            with col_del_sel:
                ticker_a_eliminar = st.selectbox(
                    f"Eliminar:", tickers_lista, key=f"del_select_{nombre_lista}"
                )
            with col_del_btn:
                if st.button(f"🗑️ Eliminar", key=f"btn_del_{nombre_lista}"):
                    if ticker_a_eliminar in st.session_state.listas_guardadas[nombre_lista]:
                        st.session_state.listas_guardadas[nombre_lista].remove(ticker_a_eliminar)
                        guardar_listas(st.session_state.listas_guardadas)
                        st.success(f"🗑️ Eliminado {ticker_a_eliminar}")
                        st.rerun()

            col_add, col_add_btn = st.columns([3, 1])
            with col_add:
                nuevo_ticker = st.text_input(f"Añadir:", key=f"add_ticker_{nombre_lista}")
            with col_add_btn:
                if st.button(f"➕ Añadir", key=f"btn_add_{nombre_lista}"):
                    if nuevo_ticker and nuevo_ticker.strip().upper() not in [t.upper() for t in st.session_state.listas_guardadas[nombre_lista]]:
                        st.session_state.listas_guardadas[nombre_lista].append(nuevo_ticker.strip().upper())
                        guardar_listas(st.session_state.listas_guardadas)
                        st.success(f"➕ Añadido {nuevo_ticker.strip().upper()}")
                        st.rerun()
                    else:
                        st.error("Vacío o duplicado")

            st.write("---")
            col_edit, col_del = st.columns([1, 1])
            with col_edit:
                nuevo_nombre = st.text_input(f"Renombrar:", value=nombre_lista, key=f"rename_{nombre_lista}")
                if nuevo_nombre != nombre_lista and st.button(f"✅ Guardar", key=f"save_name_{nombre_lista}"):
                    st.session_state.listas_guardadas[nuevo_nombre] = st.session_state.listas_guardadas.pop(nombre_lista)
                    guardar_listas(st.session_state.listas_guardadas)
                    st.success(f"Renombrada a '{nuevo_nombre}'")
                    st.rerun()
            with col_del:
                if st.button(f"🗑️ Eliminar lista", key=f"del_{nombre_lista}"):
                    del st.session_state.listas_guardadas[nombre_lista]
                    guardar_listas(st.session_state.listas_guardadas)
                    st.success(f"Lista '{nombre_lista}' eliminada.")
                    st.rerun()

    st.write("---")
    st.write("### ➕ Crear Nueva Lista")
    nombre_nueva = st.text_input("Nombre:", key="nueva_lista_nombre")
    tickers_nueva = st.text_area("Tickers (separados por comas):", key="nueva_lista_tickers")

    if st.button("💾 Guardar", key="guardar_nueva"):
        if nombre_nueva and tickers_nueva:
            tickers_limpios = [t.strip().upper() for t in tickers_nueva.replace(chr(10), ",").split(",") if t.strip()]
            st.session_state.listas_guardadas[nombre_nueva] = tickers_limpios
            guardar_listas(st.session_state.listas_guardadas)
            st.success(f"✅ Lista '{nombre_nueva}' guardada ({len(tickers_limpios)} tickers).")
            st.rerun()
        else:
            st.error("Completa nombre y tickers.")

    st.write("---")
    st.write("### 📥 Importar/Exportar Listas")
    col_imp, col_exp = st.columns(2)
    with col_imp:
        archivo_subido = st.file_uploader("Subir JSON:", type=["json"], key="upload_json")
        if archivo_subido is not None:
            try:
                listas_importadas = json.load(archivo_subido)
                st.session_state.listas_guardadas.update(listas_importadas)
                guardar_listas(st.session_state.listas_guardadas)
                st.success("✅ Listas importadas.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    with col_exp:
        json_str = json.dumps(st.session_state.listas_guardadas, indent=2)
        st.download_button(
            label="📥 Descargar JSON",
            data=json_str,
            file_name="listas_permanentes.json",
            mime="application/json",
            key="download_json"
        )

st.write("---")
st.caption("Centro de Mando Financiero Pro v6.1 | Motor de Analisis Limpio + Contexto de Caida | Streamlit + yFinance")
