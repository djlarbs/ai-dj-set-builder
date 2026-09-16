import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import io

# -----------------------------------------------------------------------------
# CAMELOT WHEEL UTILITIES
# -----------------------------------------------------------------------------
KEY_MAPPING = {
    # Key Name -> Camelot Code
    "C": "8B", "Am": "8A", "A Minor": "8A",
    "G": "9B", "Em": "9A", "E Minor": "9A",
    "D": "10B", "Bm": "10A", "B Minor": "10A",
    "A": "11B", "F#m": "11A", "F-Sharp Minor": "11A",
    "E": "12B", "C#m": "12A", "C-Sharp Minor": "12A",
    "B": "1B", "G#m": "1A", "G-Sharp Minor": "1A",
    "F#": "2B", "D#m": "2A", "D-Sharp Minor": "2A",
    "Db": "3B", "Bbm": "3A", "B-Flat Minor": "3A",
    "Ab": "4B", "Fm": "4A", "F Minor": "4A",
    "Eb": "5B", "Cm": "5A", "C Minor": "5A",
    "Bb": "6B", "Gm": "6A", "G Minor": "6A",
    "F": "7B", "Dm": "7A", "D Minor": "7A",
}

def normalize_to_camelot(key_str: str) -> str:
    """Standardizes track key into Camelot notation (e.g., '8A')."""
    if not key_str:
        return "Unknown"
    key_str = key_str.strip()
    if key_str in KEY_MAPPING:
        return KEY_MAPPING[key_str]
    # If already in Camelot format (e.g., 8A, 11B)
    if len(key_str) in [2, 3] and key_str[:-1].isdigit() and key_str[-1].upper() in ['A', 'B']:
        return key_str.upper()
    return "Unknown"

def get_compatible_camelot_keys(camelot_key: str) -> list[str]:
    """Calculates harmonically compatible keys using Camelot rules."""
    if camelot_key == "Unknown":
        return []
    number = int(camelot_key[:-1])
    letter = camelot_key[-1]
    
    same_number_other_letter = f"{number}{'B' if letter == 'A' else 'A'}"
    plus_one = f"{(number % 12) + 1}{letter}"
    minus_one = f"{12 if number - 1 == 0 else number - 1}{letter}"
    
    return [camelot_key, same_number_other_letter, plus_one, minus_one]

# -----------------------------------------------------------------------------
# XML PARSING & GENERATION
# -----------------------------------------------------------------------------
def parse_rekordbox_xml(xml_bytes: bytes) -> list[dict]:
    """Parses exported Rekordbox XML content into track objects."""
    tree = ET.ElementTree(ET.fromstring(xml_bytes))
    root = tree.getroot()
    tracks = []
    
    collection = root.find("COLLECTION")
    if collection is None:
        return tracks

    for track in collection.findall("TRACK"):
        t_id = track.get("TrackID")
        title = track.get("Name", "Unknown Track")
        artist = track.get("Artist", "Unknown Artist")
        
        try:
            bpm = float(track.get("AverageBpm", 120.0))
        except ValueError:
            bpm = 120.0
            
        raw_key = track.get("Tonality", "")
        camelot_key = normalize_to_camelot(raw_key)
        
        # Estimate energy rating (from Rating field or default to 5)
        try:
            rating = int(track.get("Rating", 100))
            energy = min(10, max(1, int(rating / 20)))  # Convert 0-255 scale to 1-10
        except ValueError:
            energy = 5

        tracks.append({
            "id": t_id,
            "title": title,
            "artist": artist,
            "bpm": round(bpm, 1),
            "raw_key": raw_key,
            "key": camelot_key,
            "energy": energy,
            "location": track.get("Location", "")
        })
    return tracks

def generate_rekordbox_playlist_xml(setlist: list[dict], playlist_name: str = "AI Generated Set") -> str:
    """Creates a new Rekordbox-importable XML containing the arranged playlist."""
    root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
    
    # Collection section
    collection = ET.SubElement(root, "COLLECTION", Entries=str(len(setlist)))
    for track in setlist:
        ET.SubElement(collection, "TRACK", {
            "TrackID": str(track["id"]),
            "Name": track["title"],
            "Artist": track["artist"],
            "AverageBpm": str(track["bpm"]),
            "Tonality": track["key"],
            "Location": track["location"]
        })
        
    # Playlists section
    playlists = ET.SubElement(root, "PLAYLISTS")
    root_node = ET.SubElement(playlists, "NODE", Type="0", Name="ROOT")
    playlist_node = ET.SubElement(root_node, "NODE", Name=playlist_name, Type="1", KeyType="0", Entries=str(len(setlist)))
    
    for track in setlist:
        ET.SubElement(playlist_node, "TRACK", Key=str(track["id"]))
        
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

# -----------------------------------------------------------------------------
# SET GENERATION ENGINE
# -----------------------------------------------------------------------------
def build_setlist(start_track: dict, library: list[dict], target_length: int, bpm_tolerance: float) -> list[dict]:
    """Generates a cohesive sequence of tracks based on BPM, Camelot key, and energy."""
    setlist = [start_track]
    used_ids = {start_track["id"]}
    current_track = start_track

    for i in range(1, target_length):
        compatible_keys = get_compatible_camelot_keys(current_track["key"])
        
        candidates = []
        for track in library:
            if track["id"] in used_ids:
                continue
                
            # Rule 1: Strict BPM Tolerance
            bpm_diff = abs(track["bpm"] - current_track["bpm"])
            if bpm_diff > bpm_tolerance:
                continue
                
            # Rule 2: Harmonic Match (Prioritize valid Camelot key)
            key_score = 0 if track["key"] in compatible_keys else 1
            
            # Rule 3: Avoid same artist back-to-back
            artist_penalty = 2 if track["artist"].lower() == current_track["artist"].lower() else 0

            # Rank candidate score (lower score = better fit)
            score = key_score + (bpm_diff * 0.5) + artist_penalty
            candidates.append((track, score))

        if not candidates:
            break

        # Pick the best candidate track
        candidates.sort(key=lambda x: x[1])
        next_track = candidates[0][0]
        
        setlist.append(next_track)
        used_ids.add(next_track["id"])
        current_track = next_track

    return setlist

# -----------------------------------------------------------------------------
# STREAMLIT UI LAYOUT
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AI DJ Set Builder", page_icon="🎧", layout="wide")

st.title("🎧 AI DJ Set Builder & Harmonic Selector")
st.markdown("Upload your **Rekordbox Collection XML** file to build seamless, harmonically aligned DJ set lists.")

# File Uploader
uploaded_file = st.sidebar.file_uploader("Upload Rekordbox XML Export", type=["xml"])

if uploaded_file is not None:
    xml_bytes = uploaded_file.read()
    library = parse_rekordbox_xml(xml_bytes)
    
    if not library:
        st.error("No valid tracks found in the XML file. Please check your export.")
    else:
        st.sidebar.success(f"Loaded {len(library)} tracks from Rekordbox XML!")

        # Sidebar Controls
        st.sidebar.header("Set Configuration")
        
        # Track Selection dropdown
        track_options = {f"{t['title']} - {t['artist']} [{t['key']}, {t['bpm']} BPM]": t for t in library}
        selected_track_label = st.sidebar.selectbox("Select Starting Track", list(track_options.keys()))
        start_track = track_options[selected_track_label]

        set_length = st.sidebar.slider("Target Number of Tracks", min_value=3, max_value=50, value=12)
        max_bpm_diff = st.sidebar.slider("Max BPM Shift Between Tracks", min_value=1.0, max_value=10.0, value=3.0, step=0.5)

        if st.sidebar.button("✨ Generate AI Setlist", type="primary"):
            setlist = build_setlist(start_track, library, set_length, max_bpm_diff)
            st.session_state["generated_set"] = setlist

        # Render Results
        if "generated_set" in st.session_state:
            setlist = st.session_state["generated_set"]
            
            st.subheader(f"Generated Setlist ({len(setlist)} Tracks)")
            
            # Display Set Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Starting BPM", f"{setlist[0]['bpm']} BPM")
            col2.metric("Ending BPM", f"{setlist[-1]['bpm']} BPM")
            col3.metric("Key Diversity", f"{len(set(t['key'] for t in setlist))} Unique Keys")

            # Output Data Table
            df = pd.DataFrame(setlist)[["id", "title", "artist", "bpm", "key", "energy"]]
            df.columns = ["ID", "Track Title", "Artist", "BPM", "Camelot Key", "Energy (1-10)"]
            st.dataframe(df, use_container_width=True)

            # File Export Options
            st.markdown("---")
            st.subheader("📥 Export Set Back to Rekordbox")
            
            col_exp1, col_exp2 = st.columns(2)
            
            # Export Rekordbox XML
            xml_data = generate_rekordbox_playlist_xml(setlist, playlist_name="AI_Curated_Set")
            col_exp1.download_button(
                label="Download Rekordbox XML",
                data=xml_data,
                file_name="AI_Curated_Set.xml",
                mime="application/xml"
            )

            # Export M3U Playlist
            m3u_data = "#EXTM3U\n" + "\n".join([f"#EXTINF:-1,{t['artist']} - {t['title']}\n{t['location']}" for t in setlist])
            col_exp2.download_button(
                label="Download M3U Playlist",
                data=m3u_data,
                file_name="AI_Curated_Set.m3u",
                mime="audio/x-mpegurl"
            )
else:
    st.info("👈 Please upload your Rekordbox XML collection file in the sidebar to get started.")
    st.markdown("""
    ### How to export from Rekordbox:
    1. Open **Rekordbox**.
    2. Go to `File` $\rightarrow$ `Export Collection in XML format`.
    3. Upload the resulting `.xml` file to this dashboard!
    """)