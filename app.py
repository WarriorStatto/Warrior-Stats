import streamlit as st
import pandas as pd

st.title("🏆 Warriors Stats")

df = pd.read_excel("skittles-import.xlsx")

st.success(f"{len(df)} rows loaded")

st.write(df.head())
