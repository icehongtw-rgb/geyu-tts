import streamlit as st
import edge_tts
from gtts import gTTS
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

# Clean White/Red CSS (Reverted forced Black styles for components)
st.markdown("""
    <style>
    /* --- GLOBAL RESET --- */
    .stApp { 
        background-color: #ffffff; 
        color: #18181b; /* Zinc-900 */
        font-family: 'Inter', system-ui, sans-serif;
    }
    
    /* --- SIDEBAR BACKGROUND --- */
    [data-testid="stSidebar"] {
        background-color: #fafafa;
        border-right: 1px solid #f4f4f5;
    }

    /* --- ALERTS --- */
    div[data-baseweb="notification"], div[data-testid="stAlert"] {
        background-color: #fef2f2 !important; /* Red-50 */
        border: 1px solid #fee2e2 !important; /* Red-100 */
        color: #991b1b !important; /* Red-800 */
    }
    div[data-testid="stAlert"] svg, div[data-baseweb="notification"] svg {
        fill: #ef4444 !important; /* Red-500 */
        color: #ef4444 !important;
    }

    /* --- CUSTOM STATUS BADGES --- */
    .status-ok { 
        background-color: #f0fdf4; /* Green-50 */
        color: #166534; /* Green-800 */
        padding: 0.75rem; 
        border-radius: 8px; 
        margin-bottom: 15px; 
        border: 1px solid #bbf7d0;
        font-size: 0.9rem;
        display: flex; align-items: center; gap: 8px;
    }
    .status-err { 
        background-color: #fef2f2; /* Red-50 */
        color: #991b1b; /* Red-800 */
        padding: 0.75rem; 
        border-radius: 8px; 
        margin-bottom: 15px; 
        border: 1px solid #fee2e2;
        font-size: 0.9rem;
    }

    /* --- TEXT AREA TWEAK (Optional: Just removing the red border radius if needed, but keeping red focus) --- */
    .stTextArea textarea { 
        border-radius: 0.75rem !important;
        font-family: monospace !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 數據定義 ---

# EDGE TTS 數據
VOICES_EDGE = {
    "簡體中文 (中國)": {
        "zh-CN-XiaoxiaoNeural": "🇨🇳 小曉 (女聲 - 活潑/推薦) 🔥",
        "zh-CN-XiaoyiNeural": "🇨🇳 小藝 (女聲 - 氣質)",
        "zh-CN-YunxiNeural": "🇨🇳 雲希 (男聲 - 帥氣)",
        "zh-CN-YunjianNeural": "🇨🇳 雲健 (男聲 - 體育)",
        "zh-CN-YunyangNeural": "🇨🇳 雲揚 (男聲 - 專業/播音)",
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

# GOOGLE TTS 數據
LANG_GOOGLE = {
    "簡體中文 (zh-cn)": "zh-cn",
    "繁體中文 (zh-tw)": "zh-tw",
    "英文 (en)": "en"
}

# 風格預設 (僅 Edge 有效)
STYLE_PRESETS = {
    "general":      {"rate": 0,   "pitch": 0},
    "affectionate": {"rate": -25, "pitch": -5},
    "cheerful":     {"rate": 15,  "pitch": 5},
    "gentle":       {"rate": -10, "pitch": -2},
    "sad":          {"rate": -30, "pitch": -8},
    "angry":        {"rate": 10,  "pitch": 8},
    "whispering":   {"rate": -30, "pitch": -10},
    "shouting":     {"rate": 10,  "pitch": 12},
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

# --- 6. 核心生成邏輯 (多引擎) ---
async def generate_audio_stream_edge(text, voice, rate_val, volume_val, pitch_val, remove_silence=False):
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

def generate_audio_stream_google(text, lang, slow=False, remove_silence=False):
    tts = gTTS(text=text, lang=lang, slow=slow)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    final_bytes = fp.getvalue()
    
    if remove_silence:
        final_bytes = trim_silence(final_bytes)
    return final_bytes

# --- 7. 介面邏輯 ---
def main():
    with st.sidebar:
        st.title("參數設定")
        st.caption("Version 1.0 / Dual Engine")
        
        if HAS_PYDUB and HAS_FFMPEG:
            st.markdown('<div class="status-ok"><span>●</span> Python 環境完整</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-err"><span>○</span> 環境缺失 (需 ffmpeg)</div>', unsafe_allow_html=True)

        # 引擎選擇
        engine = st.radio("TTS 引擎庫", ["Edge TTS (微軟/高音質)", "Google TTS (谷歌/標準)"])

        # 根據選擇顯示不同參數
        if "Edge" in engine:
            st.markdown("### 1. 語音")
            category = st.selectbox("語言區域", list(VOICES_EDGE.keys()))
            selected_voice = st.selectbox("角色選擇", list(VOICES_EDGE[category].keys()), format_func=lambda x: VOICES_EDGE[category][x])

            st.markdown("### 2. 風格 (物理模擬)")
            st.selectbox(
                "情感預設", 
                list(STYLES.keys()), 
                format_func=lambda x: STYLES[x], 
                index=0,
                key="style_selection",
                on_change=update_sliders
            )
            st.caption("透過調整語速與音調模擬情感。")

            st.markdown("### 3. 微調")
            rate = st.slider("語速 (Rate)", -100, 100, key="rate_val", format="%d%%")
            pitch = st.slider("音調 (Pitch)", -100, 100, key="pitch_val", format="%dHz")
            volume = st.slider("音量 (Volume)", -100, 100, 0, format="%d%%")

        else: # Google TTS
            st.markdown("### 1. 設定")
            st.info("Google TTS 穩定免費，但不支援語速(微調)、音調與情感調整。")
            
            selected_lang_label = st.selectbox("語言", list(LANG_GOOGLE.keys()))
            selected_lang_code = LANG_GOOGLE[selected_lang_label]
            
            google_slow = st.checkbox("慢速模式 (Slow Mode)", value=False)
            
            # 這些是為了兼容下方的函數調用，雖然Google用不到
            selected_voice = None 
            rate = 0
            pitch = 0
            volume = 0

        st.markdown("---")
        remove_silence_opt = st.checkbox("智能去靜音", value=True, disabled=not(HAS_PYDUB and HAS_FFMPEG))

    st.title("兒童語音合成工具")
    st.markdown("專為教材製作設計的批量生成引擎。")
    
    placeholder_txt = "001 蘋果\n002 香蕉\n1-1 第一課\n\n(若未輸入編號，系統將自動產生)"
    text_input = st.text_area("輸入內容 (編號 內容)", height=450, placeholder=placeholder_txt)
    
    items = []
    lines = text_input.split('\n')
    for i, line in enumerate(lines):
        if line.strip():
            parts = line.strip().split(maxsplit=1)
            if len(parts) >= 2:
                items.append((parts[0], parts[1]))
            elif len(parts) == 1:
                auto_id = f"auto_{i+1:03d}"
                items.append((auto_id, parts[0]))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button(f"開始批量生成 ({len(items)} 檔案)", type="primary", disabled=len(items)==0):
        zip_buffer = io.BytesIO()
        prog = st.progress(0)
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, (fname, txt) in enumerate(items):
                try:
                    data = b""
                    if "Edge" in engine:
                        data = asyncio.run(generate_audio_stream_edge(txt, selected_voice, rate, volume, pitch, remove_silence_opt))
                    else:
                        # Google TTS
                        data = generate_audio_stream_google(txt, selected_lang_code, google_slow, remove_silence_opt)
                        
                    zf.writestr(f"{fname}.mp3", data)
                except Exception as e:
                    st.error(f"{fname} 失敗: {e}")
                prog.progress((i+1)/len(items))
        
        st.success("生成完成！")
        st.download_button("下載 ZIP 壓縮檔", zip_buffer.getvalue(), "audio.zip", "application/zip")

if __name__ == "__main__":
    main()