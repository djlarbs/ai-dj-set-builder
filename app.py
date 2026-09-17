import io
import re
import xml.etree.ElementTree as ET
import pandas as pd
import requests
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
    .track-card { background-color: #171717; border: 1px solid #262626; border-radius: 8px; padding: 14px; margin-bottom: 6px; }
    .track-title { font-size: 1rem; font-weight: 700; color: #ffffff; }
    .track-artist { font-size: 0.88rem; color: #aaaaaa; margin-bottom: 6px; }
    .badge { display: inline-block; padding: 2px 6px; font-size: 0.72rem; font-weight: 700; border-radius: 4px; background: #262626; color: #00f2fe; margin-right: 4px; }
    .badge-harmonic { background: #0d3b2e; color: #00ffa3; border: 1px solid #00ffa3; }
    .badge-pitch { background: #3b2a0d; color: #ffb700; border: 1px solid #ffb700; }
    .badge-key-shift { background: #3a1548; color: #d946ef; border: 1px solid #d946ef; }
    .badge-cue { background: #1a2e3b; color: #38bdf8; border: 1px solid #38bdf8; }
    .set-step { background: #121820; border-left: 4px solid #00f2fe; padding: 12px 16px; margin-bottom: 8px; border-radius: 6px; }
    .wizard-header { font-size: 1.1rem; font-weight: 800; color: #00f2fe; text-transform: uppercase; margin-bottom: 12px; }
</style>
""",
    unsafe_allow_html=True,
)

# Camelot Map & Transposition System
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

# Key Transposition Shifts (±1 Semitone)
KEY_SHIFT_UP = {
    "1A": "8A",
    "2A": "9A",
    "3A": "10A",
    "4A": "11A",
    "5A": "12A",
    "6A": "1A",
    "7A": "2A",
    "8A": "3A",
    "9A": "4A",
    "10A": "5A",
    "11A": "6A",
    "12A": "7A",
    "1B": "8B",
    "2B": "9B",
    "3B": "10B",
    "4B": "11B",
    "5B": "12B",
    "6B": "1B",
    "7B": "2B",
    "8B": "3B",
    "9B": "4B",
    "10B": "5B",
    "11B": "6B",
    "12B": "7B",
}


# Enhanced Audio Preview Matcher
@st.cache_data(show_spinner=False)
def fetch_audio_preview(artist, title):
    try:
        raw_artist = artist.split("&")[0].split(",")[0].strip()
        is_remix = bool(
            re.search(r"remix|edit|mix|dub|vip", title, re.IGNORECASE)
        )

        clean_title = re.sub(r"[\(\[\{].*?[\)\]\}]", "", title).strip()
        clean_artist = re.sub(
            r"ft\.|feat\.|featuring", "", raw_artist, flags=re.IGNORECASE
        ).strip()

        query = requests.utils.quote(f"{clean_artist} {clean_title}")
        url = (
            f"https://itunes.apple.com/search?term={query}&entity=song&limit=10"
        )

        res = requests.get(url, timeout=2.5)
        if res.status_code == 200:
            results = res.json().get("results", [])

            for item in results:
                preview_url = item.get("previewUrl")
                if not preview_url:
                    continue

                itunes_title = item.get("trackName", "").lower()

                bad_keywords = [
                    "tribute",
                    "karaoke",
                    "cover",
                    "originally performed",
                    "instrumental version",
                ]
                if any(kw in itunes_title for kw in bad_keywords):
                    continue

                itunes_is_remix = bool(
                    re.search(r"remix|edit|mix|dub|vip", itunes_title, re.IGNORECASE)
                )
                if not is_remix and itunes_is_remix:
                    continue

                title_words = set(re.findall(r"\w+", clean_title.lower()))
                itunes_words = set(re.findall(r"\w+", itunes_title))

                if (
                    title_words
                    and len(title_words.intersection(itunes_words))
                    / len(title_words)
                    >= 0.5
                ):
                    return preview_url
    except Exception:
        pass
    return None


# Advanced Transition Analysis & Transposition Detector
def analyze_transition(prev_track, curr_track):
    if prev_track is None:
        return (
            "🏁 SEED TRACK",
            "0.0%",
            "Standard Pitch",
            "Outro: 32 Bars → Intro: 32 Bars",
        )

    k1, k2 = str(prev_track["Key"]), str(curr_track["Key"])
    bpm1, bpm2 = float(prev_track["BPM"]), float(curr_track["BPM"])

    pitch_str = "N/A"
    if bpm1 > 0 and bpm2 > 0:
        pct_diff = ((bpm2 - bpm1) / bpm1) * 100
        pitch_str = f"{pct_diff:+.1f}%"

    transposition_advice = "Standard Pitch"
    if k1 != "N/A" and k2 != "N/A":
        if KEY_SHIFT_UP.get(k2) in CAMELOT_MAP.get(k1, []):
            transposition_advice = "Key Lock: Shift +1 Semitone"

    if k1 == "N/A" or k2 == "N/A":
        key_rel = "Unknown Key Match"
    elif k1 == k2:
        key_rel = "Exact Key Match"
    elif k1[0:-1] == k2[0:-1]:
        key_rel = "Relative Major/Minor"
    elif k2 in CAMELOT_MAP.get(k1, []):
        key_rel = "Harmonic Match (Camelot ±1)"
    elif transposition_advice != "Standard Pitch":
        key_rel = "Compatible via Transposition"
    else:
        key_rel = "Energy Key Shift"

    e1, e2 = prev_track.get("Energy", 5), curr_track.get("Energy", 5)
    if abs(e1 - e2) >= 3:
        cue_advice = "Quick Drop Mix (16-Bar Outro / 8-Bar Intro)"
    else:
        cue_advice = "Smooth Blend (32-Bar Outro / 32-Bar Intro)"

    return key_rel, pitch_str, transposition_advice, cue_advice


# Persistent Parsers
@st.cache_data(show_spinner="Parsing Collection...")
def parse_rekordbox_xml(file_bytes):
    tree = ET.parse(io.BytesIO(file_bytes))
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


@st.cache_data(show_spinner="Parsing Playlist...")
def parse_m3u_file(file_bytes):
    lines = file_bytes.decode("utf-8", errors="ignore").splitlines()
    tracks = []
    current_title = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            parts = line.split(",", 1)
            if len(parts) > 1:
                current_title = parts[1]
        elif not line.startswith("#"):
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


# Harmonic Algorithm
def build_harmonic_set(
    seed_track, pool_df, track_count, energy_mode, prioritize_key
):
    setlist = [seed_track.to_dict()]
    used_indices = {seed_track.name}

    for step in range(1, track_count):
        current_track = setlist[-1]
        curr_bpm = current_track["BPM"]
        curr_key = current_track["Key"]
        curr_energy = current_track["Energy"]

        if energy_mode == "Gradual Ramp Up":
            target_energy = min(10, curr_energy + 1)
        elif energy_mode == "Peak Hour Drop":
            target_energy = min(10, curr_energy + 2)
        else:
            target_energy = curr_energy

        valid_keys = CAMELOT_MAP.get(curr_key, [curr_key])
        candidates = pool_df[~pool_df.index.isin(used_indices)].copy()
        if candidates.empty:
            break

        def score_candidate(row):
            score = 0
            if row["Key"] in valid_keys or curr_key == "N/A":
                score += 50 if prioritize_key else 30
            energy_diff = abs(row["Energy"] - target_energy)
            score += max(0, 30 - (energy_diff * 6))
            if curr_bpm > 0 and row["BPM"] > 0:
                bpm_diff = abs(row["BPM"] - curr_bpm)
                score += max(0, 20 - (bpm_diff * 2))
            return score

        candidates["Score"] = candidates.apply(score_candidate, axis=1)
        best_match = candidates.sort_values(by="Score", ascending=False).iloc[0]

        setlist.append(best_match.to_dict())
        used_indices.add(best_match.name)

    return setlist


# Interface Header
st.markdown(
    '<div class="hero-title">NEXT-GEN DJ SET BUILDER</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-subtitle">Harmonic Key Matching • Waveform Insights • Key Transposition • AI Curator</div>',
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

# File Processing
if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    file_ext = uploaded_file.name.split(".")[-1].lower()

    if file_ext == "xml":
        df_loaded = parse_rekordbox_xml(file_bytes)
    elif file_ext == "csv":
        df_loaded = pd.read_csv(io.BytesIO(file_bytes))
    else:
        df_loaded = parse_m3u_file(file_bytes)

    st.session_state["df"] = df_loaded
    st.session_state["last_file"] = uploaded_file.name

# Main Execution
if "df" in st.session_state and not st.session_state["df"].empty:
    df = st.session_state["df"]

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

    bpm_condition = (df["BPM"] >= bpm_range[0]) & (df["BPM"] <= bpm_range[1])
    zero_bpm_condition = df["BPM"] == 0.0

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

    # Metrics
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

    tab_crate, tab_ai_builder, tab_snapshots = st.tabs(
        [
            "🔥 Curated Crate",
            "🤖 AI Harmonic Set Builder",
            "📊 Snapshots & Comparisons",
        ]
    )

    with tab_crate:
        head_col1, head_col2 = st.columns([3, 1])
        with head_col1:
            st.write("Browse matched tracks and audition previews below:")
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
            display_df = filtered_df.head(50)
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
                    preview_url = fetch_audio_preview(
                        row["Artist"], row["Name"]
                    )
                    if preview_url:
                        col.audio(preview_url, format="audio/mp3")
                    else:
                        col.caption("🔇 Audio preview unavailable")
        else:
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    # 4-STEP WIZARD WITH GRAPH & TRANSPOSITION
    with tab_ai_builder:
        if filtered_df.empty:
            st.warning("No tracks available in the current filter selection.")
        else:
            if "wizard_step" not in st.session_state:
                st.session_state["wizard_step"] = 1

            current_step = st.session_state["wizard_step"]

            st.progress(current_step / 4)
            st.caption(f"STEP {current_step} OF 4")

            # STEP 1
            if current_step == 1:
                st.markdown(
                    '<div class="wizard-header">1: Select Genre & Vibe</div>',
                    unsafe_allow_html=True,
                )

                w_genres = st.multiselect(
                    "Target Set Genres",
                    options=available_genres,
                    default=available_genres,
                )
                w_priority = st.selectbox(
                    "Harmonic Mix Priority",
                    ["Strict Harmonic Key First", "Closest BPM First"],
                )

                step1_df = filtered_df[filtered_df["Genre"].isin(w_genres)]

                if st.button("NEXT: CHOOSE ANCHOR TRACK ➔"):
                    if step1_df.empty:
                        st.error("No tracks match the selected genres.")
                    else:
                        st.session_state["w_df"] = step1_df
                        st.session_state["w_priority"] = w_priority
                        st.session_state["wizard_step"] = 2
                        st.rerun()

            # STEP 2
            elif current_step == 2:
                st.markdown(
                    '<div class="wizard-header">2: Choose Anchor Track</div>',
                    unsafe_allow_html=True,
                )

                w_pool = st.session_state.get("w_df", filtered_df)
                track_labels = [
                    f"{row['Artist']} - {row['Name']} ({row['Key']} / {row['BPM']} BPM)"
                    for _, row in w_pool.iterrows()
                ]

                selected_idx = st.selectbox(
                    "Select Starting Track (Opener)",
                    range(len(track_labels)),
                    format_func=lambda x: track_labels[x],
                )

                nav1, nav2 = st.columns([1, 1])
                with nav1:
                    if st.button("⬅ BACK"):
                        st.session_state["wizard_step"] = 1
                        st.rerun()
                with nav2:
                    if st.button("NEXT: SET ENERGY PROFILE ➔"):
                        st.session_state["w_seed_idx"] = selected_idx
                        st.session_state["wizard_step"] = 3
                        st.rerun()

            # STEP 3
            elif current_step == 3:
                st.markdown(
                    '<div class="wizard-header">3: Set Energy Profile & Length</div>',
                    unsafe_allow_html=True,
                )

                e1, e2 = st.columns(2)
                with e1:
                    w_curve = st.selectbox(
                        "Energy Progression",
                        ["Maintain Energy", "Gradual Ramp Up", "Peak Hour Drop"],
                    )
                with e2:
                    w_length = st.number_input(
                        "Total Track Count",
                        min_value=3,
                        max_value=30,
                        value=8,
                        step=1,
                    )

                nav1, nav2 = st.columns([1, 1])
                with nav1:
                    if st.button("⬅ BACK"):
                        st.session_state["wizard_step"] = 2
                        st.rerun()
                with nav2:
                    if st.button("🚀 GENERATE AI SET"):
                        w_pool = st.session_state.get("w_df", filtered_df)
                        seed_idx = st.session_state.get("w_seed_idx", 0)
                        seed_row = w_pool.iloc[seed_idx]
                        prioritize_key = (
                            st.session_state.get("w_priority")
                            == "Strict Harmonic Key First"
                        )

                        st.session_state["staged_set"] = build_harmonic_set(
                            seed_row,
                            w_pool,
                            w_length,
                            w_curve,
                            prioritize_key,
                        )
                        st.session_state["wizard_step"] = 4
                        st.rerun()

            # STEP 4: REVIEW, ENERGY GRAPH & WAVEFORMS
            elif current_step == 4:
                st.markdown(
                    '<div class="wizard-header">4: Set Sequence & Live Energy Profile</div>',
                    unsafe_allow_html=True,
                )

                staged_list = st.session_state.get("staged_set", [])
                if staged_list:
                    export_df = pd.DataFrame(staged_list)

                    # Energy Flow Graph
                    st.markdown("##### 📈 Set Energy Flow Chart")
                    chart_data = pd.DataFrame(
                        {
                            "Track Order": [
                                f"#{i+1} {t['Name'][:12]}..."
                                for i, t in enumerate(staged_list)
                            ],
                            "Energy Rating": [
                                t["Energy"] for t in staged_list
                            ],
                        }
                    )
                    st.line_chart(
                        chart_data.set_index("Track Order"), height=200
                    )

                    st.markdown("---")

                    e_col1, e_col2, e_col3 = st.columns([2, 1, 1])
                    with e_col1:
                        if st.button("💾 SAVE SET TO SNAPSHOTS"):
                            if "saved_snapshots" not in st.session_state:
                                st.session_state["saved_snapshots"] = []
                            st.session_state["saved_snapshots"].append(
                                staged_list
                            )
                            st.success("Set saved to Snapshots tab!")

                    with e_col2:
                        st.download_button(
                            label="⚡ EXPORT (.M3U)",
                            data=generate_m3u(export_df),
                            file_name="ai_harmonic_set.m3u",
                            mime="audio/x-mpegurl",
                            use_container_width=True,
                        )
                    with e_col3:
                        if st.button("🔄 RESTART WIZARD"):
                            st.session_state["wizard_step"] = 1
                            st.rerun()

                    for i, track in enumerate(staged_list):
                        prev_track = staged_list[i - 1] if i > 0 else None
                        (
                            key_match_label,
                            pitch_shift,
                            transposition,
                            cue_advice,
                        ) = analyze_transition(prev_track, track)

                        t_col, b_col1, b_col2 = st.columns([8, 1, 1])

                        with t_col:
                            st.markdown(
                                f"""
                            <div class="set-step">
                                <strong>Track {i+1}: {track['Artist']} — {track['Name']}</strong><br>
                                <span class="badge">KEY {track['Key']}</span>
                                <span class="badge">BPM {track['BPM']}</span>
                                <span class="badge">ENERGY {track['Energy']}/10</span>
                                <span class="badge badge-harmonic">TRANSITION: {key_match_label}</span>
                                <span class="badge badge-pitch">PITCH: {pitch_shift}</span>
                                <span class="badge badge-key-shift">{transposition}</span>
                                <span class="badge badge-cue">📍 {cue_advice}</span>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                            # Synthetic Waveform Visualizer
                            wf_bg = "#1f2937"
                            wf_fill = "#00f2fe" if i % 2 == 0 else "#ff007f"
                            st.markdown(
                                f"""
                            <div style="background:{wf_bg}; height:24px; border-radius:4px; width:100%; display:flex; align-items:center; padding:0 8px; margin-bottom:12px;">
                                <div style="background:{wf_fill}; height:60%; width:15%; border-radius:2px; opacity:0.5;"></div>
                                <div style="background:{wf_fill}; height:90%; width:70%; border-radius:2px; margin:0 4px;"></div>
                                <div style="background:{wf_fill}; height:60%; width:15%; border-radius:2px; opacity:0.5;"></div>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                        with b_col1:
                            if i > 0:
                                if st.button("▲", key=f"up_{i}"):
                                    (
                                        st.session_state["staged_set"][i],
                                        st.session_state["staged_set"][i - 1],
                                    ) = (
                                        st.session_state["staged_set"][i - 1],
                                        st.session_state["staged_set"][i],
                                    )
                                    st.rerun()

                        with b_col2:
                            if i < len(staged_list) - 1:
                                if st.button("▼", key=f"down_{i}"):
                                    (
                                        st.session_state["staged_set"][i],
                                        st.session_state["staged_set"][i + 1],
                                    ) = (
                                        st.session_state["staged_set"][i + 1],
                                        st.session_state["staged_set"][i],
                                    )
                                    st.rerun()

    # SNAPSHOTS TAB
    with tab_snapshots:
        st.subheader("📊 Saved Set Snapshots")
        snapshots = st.session_state.get("saved_snapshots", [])

        if not snapshots:
            st.info(
                "No saved sets yet. Generate a set in Step 4 of the wizard and click 'SAVE SET TO SNAPSHOTS'."
            )
        else:
            for s_idx, set_item in enumerate(snapshots):
                s_df = pd.DataFrame(set_item)
                valid_b = s_df[s_df["BPM"] > 0]["BPM"]
                avg_bpm = f"{valid_b.mean():.1f}" if not valid_b.empty else "N/A"
                avg_energy = f"{s_df['Energy'].mean():.1f}"

                with st.expander(
                    f"📁 Snapshot #{s_idx+1} — {len(set_item)} Tracks | Avg BPM: {avg_bpm} | Avg Energy: {avg_energy}"
                ):
                    st.dataframe(s_df, use_container_width=True, hide_index=True)
                    st.download_button(
                        label=f"EXPORT SNAPSHOT #{s_idx+1} (.M3U)",
                        data=generate_m3u(s_df),
                        file_name=f"snapshot_set_{s_idx+1}.m3u",
                        mime="audio/x-mpegurl",
                        key=f"dl_snap_{s_idx}",
                    )

else:
    st.info("👈 Upload your music library file in the sidebar to enter the builder.")
