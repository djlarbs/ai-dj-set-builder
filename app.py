import io
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

# Page setup
st.set_page_config(
    page_title="AI DJ Set Builder & Harmonic Selector",
    page_icon="🎧",
    layout="wide",
)

st.title("🎧 AI DJ Set Builder & Harmonic Selector")
st.caption("Filter, harmonize, and export your track collection in seconds.")

# --- CAMELOT WHEEL HARMONIC MATCHING MAP ---
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


# --- XML PARSER ---
def parse_rekordbox_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    tracks = []

    for track in root.findall(".//TRACK"):
        tracks.append(
            {
                "Track ID": track.attrib.get("TrackID", "N/A"),
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


# --- M3U PLAYLIST GENERATOR ---
def generate_m3u(df):
    output = io.StringIO()
    output.write("#EXTM3U\n")
    for _, row in df.iterrows():
        title = row.get("Name", "Unknown Title")
        artist = row.get("Artist", "Unknown Artist")
        output.write(f"#EXTINF:-1,{artist} - {title}\n")
        output.write(f"{artist} - {title}.mp3\n")
    return output.getvalue()


# --- SIDEBAR CONTROLS ---
st.sidebar.header("1. Upload Collection")
uploaded_file = st.sidebar.file_uploader(
    "Upload XML, CSV, or Playlist", type=["xml", "csv", "m3u", "m3u8"]
)

st.sidebar.header("2. Set Filters")
bpm_range = st.sidebar.slider(
    "BPM Range",
    min_value=60.0,
    max_value=180.0,
    value=(80.0, 135.0),
    step=1.0,
)

energy_range = st.sidebar.slider(
    "Energy Range (Rating)", min_value=1, max_value=10, value=(1, 10), step=1
)

# --- MAIN APP LOGIC ---
if uploaded_file is not None:
    file_type = uploaded_file.name.split(".")[-1].lower()

    if file_type == "xml":
        df = parse_rekordbox_xml(uploaded_file)
    elif file_type == "csv":
        df = pd.read_csv(uploaded_file)
    else:
        lines = (
            uploaded_file.getvalue()
            .decode("utf-8", errors="ignore")
            .splitlines()
        )
        tracks = [
            {
                "Name": line,
                "Artist": "Unknown",
                "Genre": "Uncategorized",
                "BPM": 120.0,
                "Key": "N/A",
                "Energy": 5,
            }
            for line in lines
            if line and not line.startswith("#")
        ]
        df = pd.DataFrame(tracks)

    # Ensure required columns exist
    for col, default_val in [
        ("Genre", "Uncategorized"),
        ("BPM", 120.0),
        ("Energy", 5),
        ("Key", "N/A"),
    ]:
        if col not in df.columns:
            df[col] = default_val

    # Sidebar dynamic filters based on uploaded data
    available_genres = sorted(list(df["Genre"].dropna().unique()))
    selected_genres = st.sidebar.multiselect(
        "Filter by Genre",
        options=available_genres,
        default=available_genres,
    )

    available_keys = sorted(
        [k for k in df["Key"].dropna().unique() if k in CAMELOT_MAP]
    )
    selected_key = st.sidebar.selectbox(
        "Harmonic Match Target Key (Camelot)",
        options=["Any Key"] + available_keys,
    )

    # Filtering logic
    filtered_df = df[
        (df["BPM"] >= bpm_range[0])
        & (df["BPM"] <= bpm_range[1])
        & (df["Energy"] >= energy_range[0])
        & (df["Energy"] <= energy_range[1])
        & (df["Genre"].isin(selected_genres))
    ]

    if selected_key != "Any Key":
        compatible_keys = CAMELOT_MAP.get(selected_key, [selected_key])
        filtered_df = filtered_df[filtered_df["Key"].isin(compatible_keys)]

    # --- METRICS DASHBOARD ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Tracks", len(df))
    m2.metric("Matching Tracks", len(filtered_df))
    m3.metric(
        "Avg Filtered BPM",
        f"{filtered_df['BPM'].mean():.1f}" if not filtered_df.empty else "N/A",
    )
    m4.metric(
        "Top Filtered Genre",
        (
            filtered_df["Genre"].mode()[0]
            if not filtered_df.empty and not filtered_df["Genre"].mode().empty
            else "N/A"
        ),
    )

    st.markdown("---")

    # --- TRACK LIST & EXPORT SECTION ---
    col_title, col_export = st.columns([3, 1])

    with col_title:
        st.subheader("🎵 Filtered Track Collection")

    with col_export:
        if not filtered_df.empty:
            m3u_data = generate_m3u(filtered_df)
            st.download_button(
                label="📥 Export Setlist (.m3u)",
                data=m3u_data,
                file_name="ai_dj_setlist.m3u",
                mime="audio/x-mpegurl",
                use_container_width=True,
            )

    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

else:
    st.info(
        "👈 Upload your Rekordbox XML or music library file in the sidebar to build your set list."
    )
