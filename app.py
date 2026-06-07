
import streamlit as st
import yfinance as yf
import json
import os
import datetime

DB_FILE = 'datos_eurobot.json'

def cargar_datos():
    if not os.path.exists(DB_FILE):
        return {"balance": 50000.0, "acciones": 0, "historial": []}
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def guardar_datos(datos):
    with open(DB_FILE, 'w') as f:
        json.dump(datos, f)

# Lógica robusta para obtener datos
def obtener_mercado():
    # Forzamos Euro Stoxx 50 como caladero único
    df = yf.download("^STOXX50E", period="3mo", interval="1d")
    df['SMA10'] = df['Close'].rolling(window=10).mean()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    return df

def mercado_abierto():
    ahora = datetime.datetime.now()
    es_dia_laboral = ahora.weekday() < 5
    esta_en_horario = (9 <= ahora.hour < 17) or (ahora.hour == 17 and ahora.minute <= 30)
    return es_dia_laboral and esta_en_horario

st.set_page_config(page_title="Eurobot Autónomo", layout="wide")
st.title("🇪🇺 Eurobot: Autónomo - Euro Stoxx 50")

datos = cargar_datos()
df = obtener_mercado()

# Verificación de seguridad para evitar el TypeError
if not df.empty and 'Close' in df.columns:
    precio_actual = float(df['Close'].iloc[-1].item() if hasattr(df['Close'].iloc[-1], 'item') else df['Close'].iloc[-1])
    
    st.metric("Precio Actual", f"{precio_actual:.2f} €")
    st.metric("Balance", f"{datos['balance']:,.2f} €")
    st.metric("Acciones en Cartera", datos['acciones'])

    if mercado_abierto():
        st.success("Mercado ABIERTO. El bot está gestionando la pesca.")
        
        # Lógica de cruce de medias
        sma10 = df['SMA10'].iloc[-1]
        sma50 = df['SMA50'].iloc[-1]
        
        if sma10 > sma50 and datos['acciones'] == 0:
            cantidad = int(datos['balance'] // precio_actual)
            datos['balance'] -= (cantidad * precio_actual)
            datos['acciones'] = cantidad
            datos['historial'].append({"evento": "COMPRA", "precio": precio_actual})
            guardar_datos(datos)
            st.rerun()
        elif sma10 < sma50 and datos['acciones'] > 0:
            datos['balance'] += (datos['acciones'] * precio_actual)
            datos['historial'].append({"evento": "VENTA", "precio": precio_actual})
            datos['acciones'] = 0
            guardar_datos(datos)
            st.rerun()
    else:
        st.warning("Mercado CERRADO. Esperando a mañana a las 09:00.")
else:
    st.error("Error obteniendo datos del mercado. Reintentando...")
