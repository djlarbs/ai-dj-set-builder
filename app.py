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
    .status-good { color: #00ff88; font-weight: 700; }
    .status-warn { color: #ffaa00; font-weight: 700; }
</style>
""",
    unsafe_allow_html=True,
)

# Camelot Wheel Logic
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


def parse_rekordbox_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    tracks = []
    for track in root.findall(".//TRACK"):
        try:
            bpm = float(track.attrib.get("AverageBpm", "0"))
        except ValueError:
            bpm = 0.0

        try:
            raw_rating = int(track.attrib.get("Rating", "0"))
            energy = (
                max(1, min(10, round(raw_rating / 25.5))) if raw_rating > 0 else 1
            )
        except ValueError:
            energy = 1

        genre = track.attrib.get("Genre", "").strip() or "Uncategorized"
        location = track.attrib.get("Location", "")

        tracks.append(
            {
                "Track ID": track.attrib.get("TrackID", ""),
                "Name": track.attrib.get("Name", "Unknown Title"),
                "Artist": track.attrib.get("Artist", "Unknown Artist"),
                "Genre": genre,
                "BPM": round(bpm, 2),
                "Key": track.attrib.get("Tonality", "N/A"),
                "Energy": energy,
                "Location": location,
            }
        )
    return pd.DataFrame(tracks)


def generate_m3u(df):
    output = io.StringIO()
    output.write("#EXTM3U\n")
    for _, row in df.iterrows():
        output.write(f"#EXTINF:-1,{row['Artist']} - {row['Name']}\n")
        output.write(
            f"{row['Location'] if row['Location'] else row['Artist'] + ' - ' + row['Name'] + '.mp3'}\n"
        )
    return output.getvalue()


# Header Banner
st.markdown(
    '<div class="hero-title">NEXT-GEN DJ SET BUILDER</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-subtitle">Harmonic Key Matching • Dynamic Energy Curves • Transition Planner</div>',
    unsafe_allow_html=True,
)

# Initialize Session State
if "df" not in st.session_state:
    st.session_state["df"] = None
if "setlist" not in st.session_state:
    st.session_state["setlist"] = []

# Sidebar Controls
st.sidebar.markdown("### 🎛️ CRATE CONTROLS")
uploaded_file = st.sidebar.file_uploader(
    "Import Collection", type=["xml", "csv", "m3u", "m3u8"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ FILTERS & SMART CURVE")
bpm_range = st.sidebar.slider(
    "BPM Range", 60.0, 180.0, (60.0, 180.0), step=1.0
)

# Smart Energy Curve Selector
energy_preset = st.sidebar.selectbox(
    "Energy Profile Preset",
    [
        "Custom Filter",
        "Warm-Up Ramp (Energy 1-5)",
        "Peak Hour Energy (Energy 6-10)",
        "Cool Down Shift (Energy 1-4)",
    ],
)

if energy_preset == "Warm-Up Ramp (Energy 1-5)":
    energy_range = (1, 5)
elif energy_preset == "Peak Hour Energy (Energy 6-10)":
    energy_range = (6, 10)
elif energy_preset == "Cool Down Shift (Energy 1-4)":
    energy_range = (1, 4)
else:
    energy_range = st.sidebar.slider("Energy Floor", 1, 10, (1, 10), step=1)

# Main Flow
if uploaded_file is not None:
    if (
        st.session_state["df"] is None
        or st.sidebar.button("🔄 Reload File Data")
    ):
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
                        "Track ID": str(idx),
                        "Name": line,
                        "Artist": "Unknown",
                        "Genre": "Uncategorized",
                        "BPM": 0.0,
                        "Key": "N/A",
                        "Energy": 1,
                        "Location": "",
                    }
                    for idx, line in enumerate(lines)
                    if line and not line.startswith("#")
                ]
            )

        st.session_state["df"] = df_loaded

    df = st.session_state["df"]

    # Sidebar Multiselect
    available_genres = sorted(list(df["Genre"].dropna().unique()))
    selected_genres = st.sidebar.multiselect(
        "Filter Genres", options=available_genres, default=available_genres
    )

    available_keys = sorted(
        [k for k in df["Key"].dropna().unique() if k in CAMELOT_MAP]
    )
    selected_key = st.sidebar.selectbox(
        "Camelot Target Key", options=["Any Key"] + available_keys
    )

    # Apply Filters
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

    # Metrics Summary
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL TRACKS", len(df))
    m2.metric("CRATE MATCHES", len(filtered_df))
    m3.metric(
        "AVG BPM",
        f"{filtered_df['BPM'].mean():.1f}" if not filtered_df.empty else "0.0",
    )
    m4.metric(
        "SETLIST STAGED",
        f"{len(st.session_state['setlist'])} Tracks",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Workspace Tabs
    tab_crate, tab_planner = st.tabs(
        ["🔥 Curated Crate", "🎛️ Live Transition Set Planner"]
    )

    with tab_crate:
        head_col1, head_col2 = st.columns([3, 1])
        with head_col1:
            st.caption("Browse tracks and stage them into your set planner.")
        with head_col2:
            if not filtered_df.empty:
                st.download_button(
                    label="⚡ EXPORT PLAYLIST (.M3U)",
                    data=generate_m3u(filtered_df),
                    file_name="curated_crate.m3u",
                    mime="audio/x-mpegurl",
                    use_container_width=True,
                )

        display_df = filtered_df.head(100)
        cols = st.columns(2)
        for idx, (_, row) in enumerate(display_df.iterrows()):
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

                # Local audio preview if path exists
                if row["Location"].startswith("file://"):
                    local_path = row["Location"].replace("file://localhost", "").replace("file://", "")
                    try:
                        st.audio(local_path)
                    except Exception:
                        pass

                # Stage button
                track_dict = row.to_dict()
                if st.button(
                    f"➕ Add to Set Builder", key=f"add_{idx}_{row['Name']}"
                ):
                    st.session_state["setlist"].append(track_dict)
                    st.toast(f"Added {row['Name']} to Set Planner!")

    with tab_planner:
        st.subheader("🎛️ Live Transition Sequence Analysis")

        if st.session_state["setlist"]:
            setlist_df = pd.DataFrame(st.session_state["setlist"])

            col_a, col_b = st.columns([3, 1])
            with col_b:
                if st.button("🗑️ Clear Planned Setlist"):
                    st.session_state["setlist"] = []
                    st.rerun()

                if not setlist_df.empty:
                    st.download_button(
                        label="📥 Download Planned Set (.M3U)",
                        data=generate_m3u(setlist_df),
                        file_name="planned_dj_set.m3u",
                        mime="audio/x-mpegurl",
                        use_container_width=True,
                    )

            # Analyze transitions between consecutive tracks
            for i in range(len(setlist_df)):
                current = setlist_df.iloc[i]

                st.markdown(
                    f"""
                <div class="track-card" style="border-left: 4px solid #00f2fe;">
                    <div class="track-title">#{i+1} — {current['Name']}</div>
                    <div class="track-artist">{current['Artist']}</div>
                    <div>
                        <span class="badge">BPM {current['BPM']}</span>
                        <span class="badge">KEY {current['Key']}</span>
                        <span class="badge">ENERGY {current['Energy']}/10</span>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # Evaluate transition to next track
                if i < len(setlist_df) - 1:
                    nxt = setlist_df.iloc[i + 1]
                    bpm_diff = round(abs(nxt["BPM"] - current["BPM"]), 1)

                    curr_key = str(current["Key"])
                    nxt_key = str(nxt["Key"])
                    is_harmonic = (
                        curr_key in CAMELOT_MAP
                        and nxt_key in CAMELOT_MAP.get(curr_key, [])
                    )

                    bpm_status = (
                        '<span class="status-good">Smooth Dynamic Step</span>'
                        if bpm_diff <= 5.0
                        else '<span class="status-warn">Large Jump (Use Tempo Transition)</span>'
                    )
                    key_status = (
                        '<span class="status-good">Harmonic Lock</span>'
                        if is_harmonic
                        else '<span class="status-warn">Key Shift (Energy/Unrelated)</span>'
                    )

                    st.markdown(
                        f"""
                    <div style="margin-left: 20px; padding: 6px 12px; border-left: 2px dashed #444; margin-bottom: 10px;">
                        <small>⬇️ <b>TRANSITION ANALYSIS:</b> Δ {bpm_diff} BPM ({bpm_status}) | Harmonic: {key_status}</small>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info(
                "Your planner is empty! Go to the 'Curated Crate' tab and click '➕ Add to Set Builder' on any track."
            )

else:
    st.info("👈 Upload your music library file in the sidebar to enter the builder.")
