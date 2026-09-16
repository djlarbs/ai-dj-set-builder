import io
import time
import xml.etree.ElementTree as ET
import pandas as pd
import requests
import streamlit as st

# 1. PAGE SETUP
st.set_page_config(
    page_title="AI DJ SET BUILDER",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. CUSTOM CSS STYLING (BPM SUPREME DARK THEME)
st.markdown(
    """
<style>
    /* Dark Theme Core */
    .stApp {
        background-color: #0d0d0d;
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #141414;
        border-right: 1px solid #262626;
    }
    
    /* Bold Hero Title */
    .hero-title {
        font-size: 3.2rem !important;
        font-weight: 900 !important;
        letter-spacing: -1.5px;
        text-transform: uppercase;
        line-height: 1.05;
        color: #ffffff;
        margin-bottom: 0.2rem;
    }
    
    .hero-subtitle {
        color: #888888;
        font-size: 1.1rem;
        font-weight: 500;
        margin-bottom: 2rem;
    }
    
    /* Metric Scorecards */
    div[data-testid="stMetric"] {
        background: #171717;
        border: 1px solid #262626;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        color: #00f2fe;
    }

    /* Track Crate Card Style */
    .track-card {
        background-color: #171717;
        border: 1px solid #262626;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        transition: transform 0.2s, border-color 0.2s;
    }
    .track-card:hover {
        border-color: #00f2fe;
        transform: translateY(-2px);
    }
    .track-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #ffffff;
    }
    .track-artist {
        font-size: 0.95rem;
        color: #aaaaaa;
        margin-bottom: 8px;
    }
    .badge {
        display: inline-block;
        padding: 3px 8px;
        font-size: 0.75rem;
        font-weight: 700;
        border-radius: 4px;
        background: #262626;
        color: #00f2fe;
        margin-right: 6px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 3. CAMELOT HARMONIC MAP
CAMELOT_MAP = {
    "1A": ["1A", "12A", "2A", "1B"],
    "1B": ["1B", "12B", "2B", "1A"],
    "2A": ["2A", "1A", "3A", "2B"],
    "2B": ["2B", "1B", "3B", "2A"],
    "3A": ["3A", "2A", "4A", "3B"],
    "3B": ["3B", "2B", "4B", "3A"],
    "4A": ["4A", "3A", "5A", "4B"],
    "4B": ["4B", "3B", "5B", "4A"],
    "5A": ["5A", "4A", "6A", "5B"],
    "5B": ["5B", "4B", "6B", "5A"],
    "6A": ["6A", "5A", "7A", "6B"],
    "6B": ["6B", "5B", "7B", "6A"],
    "7A": ["7A", "6A", "8A", "7B"],
    "7B": ["7B", "6B", "8B", "7A"],
    "8A": ["8A", "7A", "9A", "8B"],
    "8B": ["8B", "7B", "9B", "8A"],
    "9A": ["9A", "8A", "10A", "9B"],
    "9B": ["9B", "8B", "10B", "9A"],
    "10A": ["10A", "9A", "11A", "10B"],
    "10B": ["10B", "9B", "11B", "10A"],
    "11A": ["11A", "10A", "12A", "11B"],
    "11B": ["11B", "10B", "12B", "11A"],
    "12A": ["12A", "11A", "1A", "12B"],
    "12B": ["12B", "11B", "1B", "12A"],
}


# --- HELPER FUNCTIONS ---
def parse_rekordbox_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    tracks = []
    for track in root.findall(".//TRACK"):
        tracks.append(
            {
                "Name": track.attrib.get("Name", "Unknown Title"),
                "Artist": track.attrib.get("Artist", "Unknown Artist"),
                "Genre": track.attrib.get("Genre", "Uncategorized"),
                "BPM": (
                    float(track.attrib.get("AverageBpm", 0))
                    if track.attrib.get("AverageBpm")
                    else 0.0
                ),
                "Key": track.attrib.get("Tonality", "N/A"),
                "Energy": (
                    int(track.attrib.get("Rating", 0))
                    if track.attrib.get("Rating")
                    else 1
                ),
            }
        )
    return pd.DataFrame(tracks)


def generate_m3u(df):
    output = io.StringIO()
    output.write("#EXTM3U\n")
    for _, row in df.iterrows():
        output.write(f"#EXTINF:-1,{row['Artist']} - {row['Name']}\n")
        output.write(f"{row['Artist']} - {row['Name']}.mp3\n")
    return output.getvalue()


# --- HERO HEADER ---
st.markdown(
    '<div class="hero-title">NEXT-GEN DJ SET BUILDER</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-subtitle">Harmonic Key Matching • Dynamic BPM Engine • Crate Management</div>',
    unsafe_allow_html=True,
)

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.markdown("### 🎛️ CRATE CONTROLS")
uploaded_file = st.sidebar.file_uploader(
    "Import Collection", type=["xml", "csv", "m3u", "m3u8"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ FILTERS")
bpm_range = st.sidebar.slider(
    "BPM Range", 60.0, 180.0, (80.0, 135.0), step=1.0
)
energy_range = st.sidebar.slider("Energy Floor", 1, 10, (1, 10), step=1)

# --- MAIN APP FLOW ---
if uploaded_file is not None:
    if "df" not in st.session_state:
        file_ext = uploaded_file.name.split(".")[-1].lower()
        if file_ext == "xml":
            df_loaded = parse_rekordbox_xml(uploaded_file)
        elif file_ext == "csv":
            df_loaded = pd.read_csv(uploaded_file)
        else:
            lines = (
                uploaded_file.getvalue()
                .decode("utf-8", errors="ignore")
                .splitlines()
            )
            df_loaded = pd.DataFrame(
                [
                    {
                        "Name": line,
                        "Artist": "Unknown",
                        "Genre": "Uncategorized",
                        "BPM": 0.0,
                        "Key": "N/A",
                        "Energy": 1,
                    }
                    for line in lines
                    if line and not line.startswith("#")
                ]
            )

        for col, val in [
            ("Genre", "Uncategorized"),
            ("BPM", 0.0),
            ("Energy", 1),
            ("Key", "N/A"),
        ]:
            if col not in df_loaded.columns:
                df_loaded[col] = val

        st.session_state["df"] = df_loaded

    df = st.session_state["df"]

    # Sidebar Filter Options
    genres = sorted(list(df["Genre"].dropna().unique()))
    selected_genres = st.sidebar.multiselect(
        "Genres", options=genres, default=genres
    )

    keys = sorted([k for k in df["Key"].dropna().unique() if k in CAMELOT_MAP])
    selected_key = st.sidebar.selectbox(
        "Camelot Target Key", options=["Any Key"] + keys
    )

    # Filter Logic
    filtered_df = df[
        (df["BPM"] >= bpm_range[0])
        & (df["BPM"] <= bpm_range[1])
        & (df["Energy"] >= energy_range[0])
        & (df["Energy"] <= energy_range[1])
        & (df["Genre"].isin(selected_genres))
    ]

    if selected_key != "Any Key":
        comp_keys = CAMELOT_MAP.get(selected_key, [selected_key])
        filtered_df = filtered_df[filtered_df["Key"].isin(comp_keys)]

    # DASHBOARD METRICS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL TRACKS", len(df))
    m2.metric("CRATE MATCHES", len(filtered_df))
    m3.metric(
        "AVG BPM",
        f"{filtered_df['BPM'].mean():.1f}" if not filtered_df.empty else "0.0",
    )
    m4.metric(
        "PRIMARY GENRE",
        (
            filtered_df["Genre"].mode()[0]
            if not filtered_df.empty and not filtered_df["Genre"].mode().empty
            else "N/A"
        ),
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # VIEW TOGGLE & EXPORT HEADER
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.subheader("🔥 CURATED CRATE")
    with head_col2:
        if not filtered_df.empty:
            st.download_button(
                label="⚡ EXPORT PLAYLIST (.M3U)",
                data=generate_m3u(filtered_df),
                file_name="bpm_supreme_setlist.m3u",
                mime="audio/x-mpegurl",
                use_container_width=True,
            )

    # CRATE CARDS GRID VIEW
    view_option = st.radio(
        "Display Mode",
        ["Visual Crate Cards", "Compact Table Data"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if view_option == "Visual Crate Cards":
        cols = st.columns(2)  # Two-column card grid layout
        for idx, (_, row) in enumerate(filtered_df.iterrows()):
            col = cols[idx % 2]
            with col:
                col.markdown(
                    f"""
                <div class="track-card">
                    <div class="track-title">{row['Name']}</div>
                    <div class="track-artist">{row['Artist']}</div>
                    <div>
                        <span class="badge">BPM {row['BPM']}</span>
                        <span class="badge">KEY {row['Key']}</span>
                        <span class="badge">ENERGY {row['Energy']}/10</span>
                        <span class="badge" style="color:#aaaaaa;">{row['Genre']}</span>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
    else:
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

else:
    st.info("👈 Upload your music library file in the sidebar to enter the builder.")
