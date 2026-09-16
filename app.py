import io
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="AI DJ SET BUILDER",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark Theme Styling
st.markdown(
    """
<style>
    .stApp { background-color: #0d0d0d; color: #ffffff; font-family: 'Inter', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #141414; border-right: 1px solid #262626; }
    .hero-title { font-size: 2.8rem !important; font-weight: 900 !important; letter-spacing: -1.5px; text-transform: uppercase; color: #ffffff; }
    .hero-subtitle { color: #888888; font-size: 1rem; margin-bottom: 1.5rem; }
    div[data-testid="stMetric"] { background: #171717; border: 1px solid #262626; border-radius: 8px; padding: 12px; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 800 !important; color: #00f2fe; }
    .track-card { background-color: #171717; border: 1px solid #262626; border-radius: 8px; padding: 14px; margin-bottom: 10px; }
    .track-title { font-size: 1rem; font-weight: 700; color: #ffffff; }
    .track-artist { font-size: 0.88rem; color: #aaaaaa; margin-bottom: 6px; }
    .badge { display: inline-block; padding: 2px 6px; font-size: 0.72rem; font-weight: 700; border-radius: 4px; background: #262626; color: #00f2fe; margin-right: 4px; }
</style>
""",
    unsafe_allow_html=True,
)

# Camelot Map
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


# XML Parser
def parse_rekordbox_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    tracks = []
    for track in root.findall(".//TRACK"):
        bpm_val = track.attrib.get("AverageBpm", "0")
        try:
            bpm = float(bpm_val)
        except ValueError:
            bpm = 0.0

        rating_val = track.attrib.get("Rating", "0")
        try:
            raw_rating = int(rating_val)
            energy = (
                max(1, min(10, round(raw_rating / 25.5)))
                if raw_rating > 0
                else 1
            )
        except ValueError:
            energy = 1

        genre = track.attrib.get("Genre", "").strip() or "Uncategorized"

        tracks.append(
            {
                "Name": track.attrib.get("Name", "Unknown Title"),
                "Artist": track.attrib.get("Artist", "Unknown Artist"),
                "Genre": genre,
                "BPM": round(bpm, 2),
                "Key": track.attrib.get("Tonality", "N/A"),
                "Energy": energy,
            }
        )
    return pd.DataFrame(tracks)


# M3U / M3U8 Parser
def parse_m3u_file(file_content):
    lines = file_content.decode("utf-8", errors="ignore").splitlines()
    tracks = []
    current_title = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            # Parse EXTINF metadata if available: "#EXTINF:123,Artist - Title"
            parts = line.split(",", 1)
            if len(parts) > 1:
                current_title = parts[1]
        elif not line.startswith("#"):
            # Line contains track path or title
            track_name = current_title if current_title else line
            artist = "Unknown"
            title = track_name

            if " - " in track_name:
                artist_split = track_name.split(" - ", 1)
                artist = artist_split[0]
                title = artist_split[1]

            tracks.append(
                {
                    "Name": title,
                    "Artist": artist,
                    "Genre": "Uncategorized",
                    "BPM": 0.0,
                    "Key": "N/A",
                    "Energy": 1,
                }
            )
            current_title = ""

    return pd.DataFrame(tracks)


def generate_m3u(df):
    output = io.StringIO()
    output.write("#EXTM3U\n")
    for _, row in df.iterrows():
        output.write(f"#EXTINF:-1,{row['Artist']} - {row['Name']}\n")
        output.write(f"{row['Artist']} - {row['Name']}.mp3\n")
    return output.getvalue()


# Header Section
st.markdown(
    '<div class="hero-title">NEXT-GEN DJ SET BUILDER</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-subtitle">Harmonic Key Matching • Dynamic BPM Engine • Collection Management</div>',
    unsafe_allow_html=True,
)

# Sidebar
st.sidebar.markdown("### 🎛️ CRATE CONTROLS")
uploaded_file = st.sidebar.file_uploader(
    "Import Collection", type=["xml", "csv", "m3u", "m3u8"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ FILTERS")
bpm_range = st.sidebar.slider(
    "BPM Range", 60.0, 180.0, (60.0, 180.0), step=1.0
)
energy_range = st.sidebar.slider("Energy Floor", 1, 10, (1, 10), step=1)

# Application Logic
if uploaded_file is not None:
    file_ext = uploaded_file.name.split(".")[-1].lower()

    if (
        "df" not in st.session_state
        or st.session_state.get("last_file") != uploaded_file.name
    ):
        if file_ext == "xml":
            df_loaded = parse_rekordbox_xml(uploaded_file)
        elif file_ext == "csv":
            df_loaded = pd.read_csv(uploaded_file)
        else:
            df_loaded = parse_m3u_file(uploaded_file.getvalue())

        st.session_state["df"] = df_loaded
        st.session_state["last_file"] = uploaded_file.name

    df = st.session_state["df"]

    # Dynamic Genre Selection
    available_genres = sorted(list(df["Genre"].dropna().unique()))
    selected_genres = st.sidebar.multiselect(
        "Filter Genres",
        options=available_genres,
        default=available_genres,
    )

    available_keys = sorted(
        [k for k in df["Key"].dropna().unique() if k in CAMELOT_MAP]
    )
    selected_key = st.sidebar.selectbox(
        "Camelot Target Key", options=["Any Key"] + available_keys
    )

    # Filter Logic with fallback for missing BPMs (0.0)
    bpm_condition = (df["BPM"] >= bpm_range[0]) & (df["BPM"] <= bpm_range[1])
    zero_bpm_condition = df["BPM"] == 0.0  # Keep M3U tracks without BPM data

    filtered_df = df[
        (bpm_condition | zero_bpm_condition)
        & (df["Energy"] >= energy_range[0])
        & (df["Energy"] <= energy_range[1])
        & (df["Genre"].isin(selected_genres))
    ]

    if selected_key != "Any Key":
        comp_keys = CAMELOT_MAP.get(selected_key, [selected_key])
        filtered_df = filtered_df[
            filtered_df["Key"].isin(comp_keys) | (filtered_df["Key"] == "N/A")
        ]

    # Metrics Display
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL TRACKS", len(df))
    m2.metric("CRATE MATCHES", len(filtered_df))
    valid_bpms = filtered_df[filtered_df["BPM"] > 0]["BPM"]
    m3.metric(
        "AVG BPM", f"{valid_bpms.mean():.1f}" if not valid_bpms.empty else "N/A"
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

    # Export & Output
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.subheader("🔥 CURATED CRATE")
    with head_col2:
        if not filtered_df.empty:
            st.download_button(
                label="⚡ EXPORT PLAYLIST (.M3U)",
                data=generate_m3u(filtered_df),
                file_name="ai_dj_setlist.m3u",
                mime="audio/x-mpegurl",
                use_container_width=True,
            )

    view_option = st.radio(
        "Display Mode",
        ["Visual Crate Cards", "Compact Table Data"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if view_option == "Visual Crate Cards":
        display_df = filtered_df.head(200)
        cols = st.columns(2)
        for idx, (_, row) in enumerate(display_df.iterrows()):
            col = cols[idx % 2]
            with col:
                bpm_display = (
                    f"BPM {row['BPM']}" if row["BPM"] > 0 else "BPM N/A"
                )
                col.markdown(
                    f"""
                <div class="track-card">
                    <div class="track-title">{row['Name']}</div>
                    <div class="track-artist">{row['Artist']}</div>
                    <div>
                        <span class="badge">{bpm_display}</span>
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
