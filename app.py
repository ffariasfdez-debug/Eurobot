import streamlit as st
import json
import os

# Nombre del archivo de persistencia
DB_FILE = "cartera.json"

# Cargar o inicializar la cartera
def cargar_cartera():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    else:
        return {"balance": 50000.0, "posiciones": [], "historial": []}

def guardar_cartera(cartera):
    with open(DB_FILE, "w") as f:
        json.dump(cartera, f, indent=4)

cartera = cargar_cartera()

st.title("🇪🇺 Eurobot: Simulador de Inversión")

# Sidebar de control
st.sidebar.header("Panel de Control")
st.sidebar.metric("Balance Virtual", f"{cartera['balance']:.2f} €")

# Interfaz de Simulación
st.subheader("Estado de la Cartera")
if cartera["posiciones"]:
    st.write(cartera["posiciones"])
else:
    st.info("No hay posiciones abiertas actualmente.")

if st.button("Simular Compra Semanal (2.000€)"):
    if cartera["balance"] >= 2000:
        cartera["balance"] -= 2000
        cartera["posiciones"].append({"ticker": "SAP.DE", "inversion": 2000, "fecha": "2026-06-07"})
        guardar_cartera(cartera)
        st.success("Compra simulada ejecutada con éxito.")
        st.rerun()
    else:
        st.error("Balance insuficiente para esta operación.")
