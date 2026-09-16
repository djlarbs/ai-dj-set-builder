import pandas as pd
import streamlit as st

st.title("AI DJ Set Builder & Harmonic Selector")

# Sidebar Controls
st.sidebar.header("Filter Tracks")

# Dual-handle BPM Range slider
bpm_range = st.sidebar.slider(
    "BPM Range",
    min_value=60.0,
    max_value=180.0,
    value=(120.0, 130.0),
    step=1.0,
)

# Energy Level Range slider
energy_range = st.sidebar.slider(
    "Energy Level Range", min_value=1, max_value=10, value=(1, 10), step=1
)

# Apply filters if data is loaded
if "df" in st.session_state and st.session_state["df"] is not None:
    df = st.session_state["df"]

    filtered_df = df[
        (df["BPM"] >= bpm_range[0])
        & (df["BPM"] <= bpm_range[1])
        & (df["Energy"] >= energy_range[0])
        & (df["Energy"] <= energy_range[1])
    ]

    st.write(
        f"Showing **{len(filtered_df)}** tracks matching your filter criteria:"
    )
    st.dataframe(filtered_df)
