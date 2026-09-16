import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI DJ Set Builder", layout="wide")
st.title("🎧 AI DJ Set Builder & Harmonic Selector")

# --- SIDEBAR: FILE UPLOADER & FILTERS ---
st.sidebar.header("1. Upload Collection")
uploaded_file = st.sidebar.file_uploader(
    "Upload Track Collection", type=["xml", "csv", "m3u", "m3u8"]
)

st.sidebar.header("2. Track Filters")
bpm_range = st.sidebar.slider(
    "BPM Range",
    min_value=60.0,
    max_value=180.0,
    value=(120.0, 130.0),
    step=1.0,
)
energy_range = st.sidebar.slider(
    "Energy Level Range", min_value=1, max_value=10, value=(1, 10), step=1
)


# --- FILE PARSERS ---
def parse_rekordbox_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    tracks = []
    for track in root.findall(".//TRACK"):
        tracks.append(
            {
                "Name": track.attrib.get("Name", "Unknown"),
                "Artist": track.attrib.get("Artist", "Unknown"),
                "BPM": (
                    float(track.attrib.get("AverageBpm", 0))
                    if track.attrib.get("AverageBpm")
                    else 120.0
                ),
                "Key": track.attrib.get("Tonality", "N/A"),
                "Energy": (
                    int(track.attrib.get("Rating", 0))
                    if track.attrib.get("Rating")
                    else 5
                ),
            }
        )
    return pd.DataFrame(tracks)


def parse_csv(csv_file):
    df = pd.read_csv(csv_file)
    # Ensure expected columns exist or fallback cleanly
    for col in ["BPM", "Energy"]:
        if col not in df.columns:
            df[col] = 120.0 if col == "BPM" else 5
    return df


def parse_m3u(m3u_file):
    lines = m3u_file.getvalue().decode("utf-8").splitlines()
    tracks = []
    for line in lines:
        if line.startswith("#EXTINF:"):
            # Parse line format '#EXTINF:duration,Artist - Title'
            info = line.split(",", 1)[-1]
            parts = info.split(" - ", 1)
            artist = parts[0] if len(parts) > 1 else "Unknown"
            title = parts[1] if len(parts) > 1 else parts[0]
            tracks.append(
                {
                    "Name": title,
                    "Artist": artist,
                    "BPM": 120.0,
                    "Key": "N/A",
                    "Energy": 5,
                }
            )
    return pd.DataFrame(tracks)


# --- MAIN APP LOGIC ---
if uploaded_file is not None:
    file_ext = uploaded_file.name.split(".")[-1].lower()

    if file_ext == "xml":
        df = parse_rekordbox_xml(uploaded_file)
    elif file_ext == "csv":
        df = parse_csv(uploaded_file)
    elif file_ext in ["m3u", "m3u8"]:
        df = parse_m3u(uploaded_file)
    else:
        df = pd.DataFrame()

    if not df.empty:
        filtered_df = df[
            (df["BPM"] >= bpm_range[0])
            & (df["BPM"] <= bpm_range[1])
            & (df["Energy"] >= energy_range[0])
            & (df["Energy"] <= energy_range[1])
        ]

        st.success(
            f"Loaded **{uploaded_file.name}**! Showing **{len(filtered_df)}** of **{len(df)}** tracks."
        )
        st.dataframe(filtered_df, use_container_width=True)
else:
    st.info("👈 Upload an XML, CSV, or M3U file in the sidebar to get started.")
