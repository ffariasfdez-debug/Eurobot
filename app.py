import streamlit as st
import pandas as pd

st.set_page_config(page_title="Eurobot", layout="wide")
st.title("🤖 Eurobot: Trading Autónomo")

st.write("Bienvenido al sistema Eurobot. Conectado correctamente.")

if st.button("Simular Operación"):
    st.success("El bot ha analizado el mercado y está listo.")
