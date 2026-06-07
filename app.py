import streamlit as st
import yfinance as yf
import json
import os
import datetime

DB_FILE = 'datos_eurobot.json'

# --- Funciones de Gestión de Datos ---
def cargar_datos():
    if not os.path.exists(DB_FILE):
        return {"balance": 50000.0, "acciones": 0, "historial": []}
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def guardar_datos(datos):
    with open(DB_FILE, 'w') as f:
        json.dump(datos, f)

# --- Lógica de Mercado ---
def obtener_mercado(ticker):
    df = yf.download(ticker, period="3mo", interval="1d")
    df['SMA10'] = df['Close'].rolling(window=10).mean()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    return df

def mercado_abierto():
    ahora = datetime.datetime.now()
    # Mercado europeo: Lunes a Viernes, 09:00 a 17:30
    es_dia_laboral = ahora.weekday() < 5
    esta_en_horario = (9 <= ahora.hour < 17) or (ahora.hour == 17 and ahora.minute <= 30)
    return es_dia_laboral and esta_en_horario

# --- Interfaz y Ejecución ---
st.set_page_config(page_title="Eurobot Autónomo", layout="wide")
st.title("🇪🇺 Eurobot: Modo Autónomo (Especulación)")

datos = cargar_datos()
caladero = st.sidebar.selectbox("Seleccionar Índice", ["^STOXX50E", "^GDAXI", "^IBEX"])
df = obtener_mercado(caladero)
precio_actual = float(df['Close'].iloc[-1])

st.metric("Precio Actual", f"{precio_actual:.2f} €")
st.metric("Balance", f"{datos['balance']:,.2f} €")
st.metric("Acciones en Cartera", datos['acciones'])

if mercado_abierto():
    st.success("Mercado ABIERTO. Bot monitoreando tendencias.")
    
    # Lógica de compra (Cruce alcista)
    if df['SMA10'].iloc[-1] > df['SMA50'].iloc[-1] and datos['acciones'] == 0:
        cantidad = int(datos['balance'] // precio_actual)
        if cantidad > 0:
            datos['balance'] -= (cantidad * precio_actual)
            datos['acciones'] = cantidad
            datos['historial'].append({"evento": "COMPRA", "precio": precio_actual, "cantidad": cantidad})
            guardar_datos(datos)
            st.rerun()

    # Lógica de venta (Cruce bajista)
    elif df['SMA10'].iloc[-1] < df['SMA50'].iloc[-1] and datos['acciones'] > 0:
        datos['balance'] += (datos['acciones'] * precio_actual)
        datos['historial'].append({"evento": "VENTA", "precio": precio_actual, "cantidad": datos['acciones']})
        datos['acciones'] = 0
        guardar_datos(datos)
        st.rerun()
else:
    st.warning("Mercado CERRADO. Esperando apertura (09:00 - 17:30).")

st.line_chart(df[['Close', 'SMA10', 'SMA50']])
