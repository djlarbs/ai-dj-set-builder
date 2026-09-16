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
    value=(80.0, 135.0),  # Ideal default range for Afrobeats, Dancehall, Amapiano, House & Hip Hop
    step=1.0,
)

energy_range = st.sidebar.slider(
    "Energy Level Range", min_value=1, max_value=10, value=(1, 10), step=1
)


# --- REKORDBOX XML PARSER ---
def parse_rekordbox_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    tracks = []

    for track in root.findall(".//TRACK"):
        tracks.append(
            {
                "Track ID": track.attrib.get("TrackID"),
                "Name": track.attrib.get("Name"),
                "Artist": track.attrib.get("Artist"),
                "Genre": track.attrib.get("Genre", "N/A"),
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
            {"Name": line} for line in lines if line and not line.startswith("#")
        ]
        df = pd.DataFrame(tracks)

    # Filter data based on BPM and Energy
    if "BPM" in df.columns and "Energy" in df.columns:
        filtered_df = df[
            (df["BPM"] >= bpm_range[0])
            & (df["BPM"] <= bpm_range[1])
            & (df["Energy"] >= energy_range[0])
            & (df["Energy"] <= energy_range[1])
        ]
    else:
        filtered_df = df

    st.success(
        f"Successfully loaded library! Showing **{len(filtered_df)}** of **{len(df)}** tracks."
    )
    st.dataframe(filtered_df, use_container_width=True)

else:
    st.info(
        "👈 Upload your Rekordbox XML or collection file in the sidebar to start filtering your tracks."
    )
