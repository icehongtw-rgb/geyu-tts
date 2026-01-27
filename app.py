import streamlit as st
import edge_tts
import asyncio
import zipfile
import io
import shutil
import sys

# --- 1. 環境檢測 ---
HAS_FFMPEG = False
HAS_PYDUB = False

if shutil.which("ffmpeg"):
    HAS_FFMPEG = True

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

# --- 2. 設定頁面 ---
st.set_page_config(page_title="格育 - 兒童語音工具", page_icon="🧩", layout="wide")

# Minimalist Monochrome CSS with Deep Overrides
st.markdown("""
    <style>
    /* --- GLOBAL RESET --- */
    .stApp { 
        background-color: #ffffff; 
        color: #18181b; /* Zinc-900 */
        font-family: 'Inter', system-ui, sans-serif;
    }
    
    /* --- 1. REMOVE RED FROM DROPDOWNS (Selectbox) --- */
    /* Normal state */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border-color: #e4e4e7 !important; /* Zinc-200 */
        color: #18181b !important;
    }
    /* Hover state */
    div[data-baseweb="select"] > div:hover {
        border-color: #a1a1aa !important; /* Zinc-400 */
    }
    /* Focus/Active state (The "Red Flash" Fix) */
    div[data-baseweb="select"] > div:focus-within,
    div[data-baseweb="select"] > div:active {
        border-color: #18181b !important; /* Black */
        box-shadow: 0 0 0 1px #18181b !important;
    }
    /* Dropdown menu items selection color */
    li[aria-selected="true"] {
        background-color: #f4f4f5 !important; /* Zinc-100 */
        color: #18181b !important;
    }

    /* --- 2. REMOVE RED FROM TEXTAREAS & INPUTS --- */
    .stTextArea textarea { 
        min-height: 500px !important;
        border-radius: 0.75rem !important;
        border: 1px solid #e4e4e7 !important;
        background-color: #ffffff !important;
        font-family: monospace !important;
        caret-color: #18181b !important; /* Cursor color */
        padding: 1.5rem !important;
        line-height: 2rem !important;
        font-size: 0.875rem !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
    }
    /* Focus state */
    .stTextArea textarea:focus {
        border-color: #18181b !important;
        box-shadow: 0 0 0 1px #18181b !important;
    }

    /* --- 3. REMOVE RED FROM SLIDERS --- */
    /* The Thumb (Handle) */
    div[data-baseweb="slider"] div[role="slider"] {
        background-color: #18181b !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
    }
    /* The Filled Track (Progress) */
    /* Streamlit uses inline styles for the fill color, usually the primary color. 
       We use a wildcard style matcher or specific hierarchy to override. */
    div[data-baseweb="slider"] div[style*="background-color: rgb(255, 75, 75)"] {
        background-color: #18181b !important;
    }
    div[data-baseweb="slider"] div[style*="background-color: rgb(255, 74, 75)"] { /* sometimes slight variation */
        background-color: #18181b !important;
    }
    /* Fallback for newer Streamlit versions: Target the first child div of the track container that has a color */
    div[data-baseweb="slider"] > div > div > div > div {
        background-color: #18181b !important;
    }

    /* --- 4. REMOVE RED FROM CHECKBOXES --- */
    /* Checked State Background */
    div[data-baseweb="checkbox"] span[class*="Checked"] {
        background-color: #18181b !important;
        border-color: #18181b !important;
    }
    /* Checkmark Icon */
    div[data-baseweb="checkbox"] span[class*="Checked"] div {
        color: #ffffff !important;
    }
    /* Focus Ring */
    div[data-baseweb="checkbox"]:focus-within span {
        box-shadow: 0 0 0 2px rgba(24, 24, 27, 0.2) !important;
    }

    /* --- 5. BUTTON STYLES (MATCHING APP.TSX) --- */
    div.stButton > button, div.stDownloadButton > button {
        width: 100%;
        background-color: #18181b !important;
        color: white !important;
        border-radius: 0.75rem !important;
        border: none !important;
        padding: 1rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        font-size: 0.875rem !important;
        transition: all 0.2s !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: #000000 !important;
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
    }
    div.stButton > button:disabled {
        background-color: #f4f4f5 !important;
        color: #a1a1aa !important;
        cursor: not-allowed;
        box-shadow: none !important;
        transform: none !important;
    }

    /* --- 6. ALERTS & PROGRESS BARS --- */
    .stProgress > div > div > div > div {
        background-color: #18181b !important;
    }
    div[data-baseweb="notification"], div[data-testid="stAlert"] {
        background-color: #f4f4f5 !important;
        border: 1px solid #e4e4e7 !important;
        color: #18181b !important;
    }
    div[data-testid="stAlert"] svg, div[data-baseweb="notification"] svg {
        fill: #18181b !important;
        color: #18181b !important;
    }

    /* --- SIDEBAR --- */
    [data-testid="stSidebar"] {
        background-color: #fafafa;
        border-right: 1px solid #f4f4f5;
    }
    .status-ok { 
        background-color: #f4f4f5; 
        color: #52525b; 
        padding: 0.75rem; 
        border-radius: 8px; 
        margin-bottom: 15px; 
        border: 1px solid #e4e4e7;
        font-size: 0.9rem;
        display: flex; align-items: center; gap: 8px;
    }
    .status-err { 
        background-color: #f4f4f5; 
        color: #52525b; 
        padding: 0.75rem; 
        border-radius: 8px; 
        margin-bottom: 15px; 
        border: 1px solid #e4e4e7;
        font-size: 0.9rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 數據定義 (已重新排序：女聲在前，男聲在後) ---
VOICES = {
    "簡體中文 (中國)": {
        "zh-CN-XiaoxiaoNeural": "🇨🇳 小曉 (女聲 - 活潑/推薦) 🔥",
        "zh-CN-XiaoyiNeural": "🇨🇳 小藝 (女聲 - 氣質)",
        "zh-CN-XiaohanNeural": "🇨🇳 曉涵 (女聲 - 溫暖)",
        "zh-CN-YunxiNeural": "🇨🇳 雲希 (男聲 - 帥氣)",
        "zh-CN-YunjianNeural": "🇨🇳 雲健 (男聲 - 體育)",
    },
    "繁體中文 (台灣)": {
        "zh-TW-HsiaoChenNeural": "🇹🇼 曉臻 (女聲 - 溫柔/標準)",
        "zh-TW-HsiaoYuNeural": "🇹🇼 曉雨 (女聲 - 清晰)",
        "zh-TW-YunJheNeural": "🇹🇼 雲哲 (男聲 - 沉穩)",
    },
    "英文 (美國)": {
        "en-US-AnaNeural": "🇺🇸 Ana (女聲 - 兒童/可愛)",
        "en-US-AriaNeural": "🇺🇸 Aria (女聲 - 標準)",
        "en-US-GuyNeural": "🇺🇸 Guy (男聲 - 標準)",
    }
}

# 風格預設參數庫 (物理模擬法)
STYLE_PRESETS = {
    "general":      {"rate": 0,   "pitch": 0},
    "affectionate": {"rate": -25, "pitch": -5}, # 哄孩子
    "cheerful":     {"rate": 15,  "pitch": 5},  # 開心
    "gentle":       {"rate": -10, "pitch": -2}, # 溫和
    "sad":          {"rate": -30, "pitch": -8}, # 悲傷
    "angry":        {"rate": 10,  "pitch": 8},  # 生氣
    "whispering":   {"rate": -30, "pitch": -10},# 耳語
    "shouting":     {"rate": 10,  "pitch": 12}, # 大喊
}

STYLES = {
    "general": "預設 (General)",
    "affectionate": "❤️ 親切/哄孩子",
    "cheerful": "😄 開心",
    "gentle": "☁️ 溫和",
    "sad": "😢 悲傷",
    "angry": "😡 生氣",
    "whispering": "🤫 耳語",
    "shouting": "📢 大喊",
}

# --- 4. Session State 初始化 ---
if 'rate_val' not in st.session_state:
    st.session_state['rate_val'] = 0
if 'pitch_val' not in st.session_state:
    st.session_state['pitch_val'] = 0

def update_sliders():
    selected_style = st.session_state.style_selection
    if selected_style in STYLE_PRESETS:
        st.session_state.rate_val = STYLE_PRESETS[selected_style]["rate"]
        st.session_state.pitch_val = STYLE_PRESETS[selected_style]["pitch"]

# --- 5. 輔助功能 ---
def trim_silence(audio_bytes):
    if not HAS_PYDUB or not HAS_FFMPEG: return audio_bytes 
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        def detect_leading(sound, silence_threshold=-50.0, chunk_size=10):
            trim_ms = 0
            while trim_ms < len(sound) and sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold:
                trim_ms += chunk_size
            return trim_ms
        start_trim = detect_leading(audio)
        end_trim = detect_leading(audio.reverse())
        if start_trim + end_trim < len(audio):
            trimmed = audio[start_trim:len(audio)-end_trim]
            out = io.BytesIO()
            trimmed.export(out, format="mp3")
            return out.getvalue()
    except: pass 
    return audio_bytes

# --- 6. 核心生成邏輯 (純參數版) ---
async def generate_audio_stream(text, voice, rate_val, volume_val, pitch_val, remove_silence=False):
    rate_str = f"{rate_val:+d}%"
    pitch_str = f"{pitch_val:+d}Hz"
    volume_str = f"{volume_val:+d}%"
    
    communicate = edge_tts.Communicate(
        text, 
        voice, 
        rate=rate_str, 
        volume=volume_str, 
        pitch=pitch_str
    )

    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
    
    final_bytes = audio_data.getvalue()
    
    if remove_silence:
        final_bytes = trim_silence(final_bytes)
        
    return final_bytes

# --- 7. 介面邏輯 ---
def main():
    with st.sidebar:
        st.title("參數設定")
        st.caption("Version 19.1 / Monochrome")
        
        if HAS_PYDUB and HAS_FFMPEG:
            st.markdown('<div class="status-ok"><span>●</span> Python 環境完整</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-err"><span>○</span> 環境缺失 (需 ffmpeg)</div>', unsafe_allow_html=True)

        st.markdown("### 1. 語音")
        category = st.selectbox("語言區域", list(VOICES.keys()))
        selected_voice = st.selectbox("角色選擇", list(VOICES[category].keys()), format_func=lambda x: VOICES[category][x])

        st.markdown("### 2. 風格 (物理模擬)")
        st.selectbox(
            "情感預設", 
            list(STYLES.keys()), 
            format_func=lambda x: STYLES[x], 
            index=0,
            key="style_selection",
            on_change=update_sliders
        )
        st.caption("透過調整語速與音調模擬情感，適用所有角色。")

        st.markdown("### 3. 微調")
        rate = st.slider("語速 (Rate)", -100, 100, key="rate_val", format="%d%%")
        pitch = st.slider("音調 (Pitch)", -100, 100, key="pitch_val", format="%dHz")
        volume = st.slider("音量 (Volume)", -100, 100, 0, format="%d%%")

        st.markdown("---")
        remove_silence_opt = st.checkbox("智能去靜音", value=True, disabled=not(HAS_PYDUB and HAS_FFMPEG))

    st.title("兒童語音合成工具")
    st.markdown("專為教材製作設計的批量生成引擎。")
    
    # 這裡的 placeholder 改用 f-string 來包含換行符號，避免排版問題
    placeholder_txt = "001 蘋果\n002 香蕉\n1-1 第一課\n\n(若未輸入編號，系統將自動產生)"
    text_input = st.text_area("輸入內容 (編號 內容)", height=450, placeholder=placeholder_txt)
    
    items = []
    lines = text_input.split('\n')
    for i, line in enumerate(lines):
        if line.strip():
            # Robust parsing:
            parts = line.strip().split(maxsplit=1)
            if len(parts) >= 2:
                items.append((parts[0], parts[1]))
            elif len(parts) == 1:
                auto_id = f"auto_{i+1:03d}"
                items.append((auto_id, parts[0]))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 使用 container 來包裹按鈕，雖然 st.button 無法直接 width:100%，但 CSS 會強制覆寫
    if st.button(f"開始批量生成 ({len(items)} 檔案)", type="primary", disabled=len(items)==0):
        zip_buffer = io.BytesIO()
        
        # 自定義進度條樣式已在上方 CSS 設定為黑色
        prog = st.progress(0)
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, (fname, txt) in enumerate(items):
                try:
                    data = asyncio.run(generate_audio_stream(txt, selected_voice, rate, volume, pitch, remove_silence_opt))
                    zf.writestr(f"{fname}.mp3", data)
                except Exception as e:
                    st.error(f"{fname} 失敗: {e}")
                prog.progress((i+1)/len(items))
        
        # 這裡的 success 樣式已在上方 CSS 設定為灰白配色，不再是綠色
        st.success("生成完成！")
        
        # 下載按鈕也會繼承上方的全寬黑按鈕樣式
        st.download_button("下載 ZIP 壓縮檔", zip_buffer.getvalue(), "audio.zip", "application/zip")

if __name__ == "__main__":
    main()