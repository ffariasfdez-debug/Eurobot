

import streamlit as st
import yfinance as yf
import json
import os
import datetime

DB_FILE = 'datos_eurobot.json'

# --- Gestión de Datos ---
def cargar_datos():
    if not os.path.exists(DB_FILE):
        return {"balance": 50000.0, "posiciones": {}, "historial": []}
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def guardar_datos(datos):
    with open(DB_FILE, 'w') as f:
        json.dump(datos, f)

# --- Lógica de Pesca en 3 Caladeros ---
CALADEROS = ["^STOXX50E", "^GDAXI", "^IBEX"]

def analizar_caladeros():
    resultados = {}
    for ticker in CALADEROS:
        df = yf.download(ticker, period="3mo", interval="1d")
        sma10 = df['Close'].rolling(window=10).mean().iloc[-1]
        sma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        resultados[ticker] = {"tendencia": sma10 > sma50, "precio": df['Close'].iloc[-1]}
    return resultados

datos = cargar_datos()
mercado = analizar_caladeros()

st.title("🇪🇺 Eurobot: Pescador Autónomo")

# Ejecución autónoma
for ticker, info in mercado.items():
    # Si detecta tendencia alcista y no tenemos nada ahí: COMPRA
    if info['tendencia'] and ticker not in datos['posiciones']:
        datos['posiciones'][ticker] = info['precio']
        datos['historial'].append(f"Compra autónoma en {ticker}")
        guardar_datos(datos)
    
    # Si la tendencia se rompe: VENTA
    elif not info['tendencia'] and ticker in datos['posiciones']:
        del datos['posiciones'][ticker]
        datos['historial'].append(f"Venta autónoma en {ticker} para asegurar beneficio")
        guardar_datos(datos)

# Visualización del estado del bot
st.write("### Estado de los Caladeros")
for ticker, info in mercado.items():
    estado = "✅ Tendencia Alcista (Pesca Activa)" if info['tendencia'] else "❌ Tendencia Bajista (Fuera del agua)"
    st.write(f"**{ticker}:** {estado}")

st.write("### Posiciones Actuales")
st.json(datos['posiciones'])
