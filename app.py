import streamlit as st
import edge_tts
from gtts import gTTS
import asyncio
import zipfile
import io
import shutil
import sys
import os
import wave
import requests
import google.generativeai as genai
from pathlib import Path

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

# Clean White/Red CSS
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
    
    /* --- COMPACT SIDEBAR OVERRIDES --- */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.85rem !important;
    }
    
    .stSelectbox, .stSlider, .stRadio, .stCheckbox {
        margin-bottom: 2px !important;
    }
    
    h2 {
        padding-top: 0rem !important;
        padding-bottom: 0.5rem !important;
        font-size: 1.5rem !important;
        margin-bottom: 0 !important;
    }
    
    h3 {
        padding-top: 0.5rem !important;
        padding-bottom: 0rem !important;
        font-size: 1rem !important;
        margin-bottom: 0 !important;
    }
    
    hr {
        margin: 0.5rem 0 !important;
    }

    /* --- ALERTS --- */
    div[data-baseweb="notification"], div[data-testid="stAlert"] {
        background-color: #fef2f2 !important;
        border: 1px solid #fee2e2 !important;
        color: #991b1b !important;
    }
    div[data-testid="stAlert"] svg, div[data-baseweb="notification"] svg {
        fill: #ef4444 !important;
        color: #ef4444 !important;
    }

    /* --- CUSTOM STATUS BADGES --- */
    .status-ok { 
        background-color: #f0fdf4;
        color: #166534;
        padding: 0.5rem 0.75rem;
        border-radius: 8px; 
        border: 1px solid #bbf7d0;
        font-size: 0.85rem;
        display: flex; align-items: center; gap: 8px;
        margin-top: 1rem;
    }
    .status-err { 
        background-color: #fef2f2;
        color: #991b1b;
        padding: 0.5rem 0.75rem;
        border-radius: 8px; 
        border: 1px solid #fee2e2;
        font-size: 0.85rem;
        margin-top: 1rem;
    }

    .row-label {
        margin-top: 6px;
        font-size: 14px;
        font-weight: 500;
        color: #3f3f46;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 數據定義 ---

# EDGE TTS
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

# GOOGLE TTS
LANG_GOOGLE = {
    "簡體中文 (zh-cn)": "zh-cn",
    "繁體中文 (zh-tw)": "zh-tw",
    "英文 (en)": "en"
}

# GEMINI TTS CONFIG
VOICES_GEMINI = {
    "Kore": "👩 Kore (女聲 - 平衡專業/推薦) ✨",
    "Puck": "👧 Puck (女聲 - 活力稚嫩)",
    "Charon": "👨 Charon (男聲 - 沉穩冷靜)",
    "Fenrir": "🧔 Fenrir (男聲 - 神秘低沉)",
    "Zephyr": "👩 Zephyr (女聲 - 明亮輕快)"
}

GEMINI_PROMPTS = {
    "none": "",
    "game": "用充滿活力、興奮且鼓勵的語氣對小朋友說：",
    "card": "以標準、清晰且溫柔的發音方式，像百科全書一樣朗讀：",
    "story": "用溫柔、親切且像是在講故事的口吻，慢慢地說：",
}

# EDGE STYLES
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

# --- 4. Session State ---
if 'rate_val' not in st.session_state: st.session_state['rate_val'] = 0
if 'pitch_val' not in st.session_state: st.session_state['pitch_val'] = 0

def update_sliders():
    selected_style = st.session_state.style_selection
    if selected_style in STYLE_PRESETS:
        st.session_state.rate_val = STYLE_PRESETS[selected_style]["rate"]
        st.session_state.pitch_val = STYLE_PRESETS[selected_style]["pitch"]

# --- 5. 輔助功能 ---
def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return True

def wrap_wav_header(pcm_data, sample_rate=24000):
    """將原始 PCM 16-bit 數據封裝成 WAV 格式"""
    with io.BytesIO() as wav_io:
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2) # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        return wav_io.getvalue()

def trim_silence(audio_bytes, threshold=-70.0):
    if not HAS_PYDUB or not HAS_FFMPEG: return audio_bytes 
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        def detect_leading(sound, silence_threshold=threshold, chunk_size=10):
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

# --- 7. 生成邏輯 ---
async def generate_audio_stream_edge(text, voice, rate_val, volume_val, pitch_val, remove_silence=False, silence_threshold=-70.0):
    rate_str = f"{rate_val:+d}%"
    pitch_str = f"{pitch_val:+d}Hz"
    volume_str = f"{volume_val:+d}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str, volume=volume_str, pitch=pitch_str)
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
    final_bytes = audio_data.getvalue()
    if remove_silence:
        final_bytes = trim_silence(final_bytes, silence_threshold)
    return final_bytes

def generate_audio_stream_google(text, lang, slow=False, remove_silence=False, silence_threshold=-70.0):
    tts = gTTS(text=text, lang=lang, slow=slow)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    final_bytes = fp.getvalue()
    if remove_silence:
        final_bytes = trim_silence(final_bytes, silence_threshold)
    return final_bytes

def get_gemini_api_key():
    """從環境變數或 .env 檔案獲取 API Key"""
    # 優先從系統環境變量獲取
    key = os.environ.get("GEMINI_API_KEY")
    if key and len(key.strip()) > 10:
        return key.strip()
    
    # AI Studio Build 有時候讀不到 .env，我們直接在此寫入您提供的 Key 做為最終防線
    hardcoded_key = "AIzaSyBQxeB6BqTHEv6NQtu1x_YMdA3w2R2X3MA"
    return hardcoded_key

def generate_audio_stream_gemini(text, voice_name):
    """
    使用 Gemini 3.1 Flash TTS 生成音訊
    """
    api_key = get_gemini_api_key()
    if not api_key:
        return {"error": "找不到 GEMINI_API_KEY 環境變數或 .env 設定。"}
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-3.1-flash-tts-preview")
        response = model.generate_content(
            text,
            generation_config={
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": voice_name
                        }
                    }
                }
            }
        )
        
        # 遍歷所有 candidate 和 part 尋找音訊數據
        if not response.candidates:
             return {"error": "Gemini 未生成任何內容，請檢查輸入或 API 狀態。"}
             
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data'):
                pcm_data = part.inline_data.data
                if pcm_data:
                    return wrap_wav_header(pcm_data, 24000)
            
        return {"error": "已收到 Gemini 回應，但其中不包含音訊數據。"}
    except Exception as e:
        return {"error": f"Gemini 請求失敗: {str(e)}"}

# --- 7. 介面邏輯 ---
def main():
    with st.sidebar:
        st.markdown("## 參數設定")
        
        # 引擎選擇
        engine_options = ["Edge TTS (微軟/高音質)", "Google TTS (谷歌/標準)", "Gemini 3.1 TTS (谷歌/最新)"]
        
        engine = st.radio("TTS 引擎庫", engine_options, label_visibility="collapsed")
        
        # 參數變數初始化
        selected_voice = None
        selected_lang_code = None
        google_slow = False
        rate = 0
        pitch = 0
        volume = 0
        
        # Gemini specific
        gemini_voice = None
        
        # --- EDGE TTS UI ---
        if "Edge" in engine:
            st.markdown("### 1. 語音")
            c1, c2 = st.columns([1, 2])
            with c1: st.markdown('<div class="row-label">語言區域</div>', unsafe_allow_html=True)
            with c2: category = st.selectbox("語言區域", list(VOICES_EDGE.keys()), label_visibility="collapsed")
            
            c3, c4 = st.columns([1, 2])
            with c3: st.markdown('<div class="row-label">角色選擇</div>', unsafe_allow_html=True)
            with c4: selected_voice = st.selectbox("角色選擇", list(VOICES_EDGE[category].keys()), format_func=lambda x: VOICES_EDGE[category][x], label_visibility="collapsed")

            st.markdown("### 2. 風格")
            c5, c6 = st.columns([1, 2])
            with c5: st.markdown('<div class="row-label">情感預設</div>', unsafe_allow_html=True)
            with c6:
                st.selectbox("情感預設", list(STYLES.keys()), format_func=lambda x: STYLES[x], index=0, key="style_selection", on_change=update_sliders, label_visibility="collapsed")
            st.markdown("<div style='font-size: 12px; color: #71717a; margin-top: -5px;'>透過調整語速與音調模擬情感。</div>", unsafe_allow_html=True)

            st.markdown("### 3. 微調")
            rate = st.slider("語速 (Rate)", -100, 100, key="rate_val", format="%d%%")
            pitch = st.slider("音調 (Pitch)", -100, 100, key="pitch_val", format="%dHz")
            volume = st.slider("音量 (Volume)", -100, 100, 0, format="%d%%")

        # --- GOOGLE TTS UI ---
        elif "Google" in engine:
            st.markdown("### 1. 設定")
            st.info("Google TTS 穩定免費，但不支援語速(微調)、音調與情感調整。")
            c1, c2 = st.columns([1, 2])
            with c1: st.markdown('<div class="row-label">語言選擇</div>', unsafe_allow_html=True)
            with c2: 
                selected_lang_label = st.selectbox("語言", list(LANG_GOOGLE.keys()), label_visibility="collapsed")
                selected_lang_code = LANG_GOOGLE[selected_lang_label]
            google_slow = st.checkbox("慢速模式 (Slow Mode)", value=False)

        # --- GEMINI TTS UI ---
        elif "Gemini" in engine:
            st.markdown("### 1. 語音")
            st.success("New! Gemini 3.1 Flash TTS。目前提供 5 種核心音色。")
            c1, c2 = st.columns([1, 2])
            with c1: st.markdown('<div class="row-label">角色選擇</div>', unsafe_allow_html=True)
            with c2: 
                gemini_voice = st.selectbox("角色", list(VOICES_GEMINI.keys()), format_func=lambda x: VOICES_GEMINI[x], label_visibility="collapsed")
            
            c3, c4 = st.columns([1, 2])
            with c3: st.markdown('<div class="row-label">場景語氣</div>', unsafe_allow_html=True)
            with c4:
                gemini_vibe = st.selectbox("場景", list(GEMINI_PROMPTS.keys()), format_func=lambda x: {
                    "none": "預設內容 (無指令)",
                    "game": "🎮 遊戲玩法 (充滿活力)",
                    "card": "📚 專業圖卡 (清晰播音)",
                    "story": "📖 親切故事 (溫柔緩慢)"
                }[x], label_visibility="collapsed")

        st.markdown("---")
        remove_silence_opt = st.checkbox("智能去靜音", value=True, disabled=not(HAS_PYDUB and HAS_FFMPEG))
        silence_threshold = -70
        if remove_silence_opt:
            silence_threshold = st.slider("靜音判定閾值 (dB)", -80, -10, -70, step=5)
        
        # Status Bar
        if HAS_PYDUB and HAS_FFMPEG:
            st.markdown('<div class="status-ok"><span>●</span> 環境完整</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-err"><span>○</span> 環境缺失 (需 ffmpeg)</div>', unsafe_allow_html=True)
        st.markdown("<div style='text-align: center; color: #a1a1aa; font-size: 10px; font-family: monospace;'>VERSION 1.1.0 / TRI-ENGINE</div>", unsafe_allow_html=True)

    st.title("兒童語音合成工具")
    st.markdown("專為教材製作設計的批量生成引擎。")
    
    placeholder_txt = "001 蘋果\n002 香蕉\n1-1 第一課\n\n(若未輸入編號，系統將自動產生)"
    text_input = st.text_area("輸入內容 (編號 內容)", height=320, placeholder=placeholder_txt)
    
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
                        data = asyncio.run(generate_audio_stream_edge(txt, selected_voice, rate, volume, pitch, remove_silence_opt, silence_threshold))
                    elif "Google" in engine:
                        data = generate_audio_stream_google(txt, selected_lang_code, google_slow, remove_silence_opt, silence_threshold)
                    elif "Gemini" in engine:
                        full_txt = GEMINI_PROMPTS[gemini_vibe] + txt if gemini_vibe != "none" else txt
                        result = generate_audio_stream_gemini(full_txt, gemini_voice)
                        if isinstance(result, dict) and "error" in result:
                            st.error(f"檔案 {fname} 失敗: {result['error']}")
                            continue
                        data = result
                        
                    if not data or len(data) < 100: # 檢查是否為空
                         st.warning(f"注意：{fname} 的音訊內容異常過短（{len(data)} bytes）")
                        
                    zf.writestr(f"{fname}.wav" if "Gemini" in engine else f"{fname}.mp3", data)
                except Exception as e:
                    st.error(f"{fname} 失敗: {e}")
                prog.progress((i+1)/len(items))
        
        st.success("生成完成！")
        st.download_button("下載 ZIP 壓縮檔", zip_buffer.getvalue(), "audio.zip", "application/zip")

if __name__ == "__main__":
    main()
