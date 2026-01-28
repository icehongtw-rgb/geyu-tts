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
from pathlib import Path

# --- 1. 環境檢測 ---
HAS_FFMPEG = False
HAS_PYDUB = False
HAS_PIPER = False

if shutil.which("ffmpeg"):
    HAS_FFMPEG = True

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

try:
    from piper.voice import PiperVoice
    HAS_PIPER = True
except ImportError:
    HAS_PIPER = False

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
        gap: 0.5rem !important;
    }
    
    .stSelectbox, .stSlider, .stRadio, .stCheckbox {
        margin-bottom: -5px !important;
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

# PIPER TTS CONFIG
PIPER_MODELS = {
    "zh_CN-huayan-medium": {
        "name": "🇨🇳 Huayan (華顏 - 自然女聲) 🔥",
        "repo": "rhasspy/piper-voices",
        "file_onnx": "zh_CN/huayan/medium/zh_CN-huayan-medium.onnx",
        "file_json": "zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json"
    },
    "zh_CN-xiaou-medium": {
        "name": "🇨🇳 Xiaou (小優 - 溫柔女聲)",
        "repo": "rhasspy/piper-voices",
        "file_onnx": "zh_CN/xiaou/medium/zh_CN-xiaou-medium.onnx",
        "file_json": "zh_CN/xiaou/medium/zh_CN-xiaou-medium.onnx.json"
    }
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

def adjust_pitch_ffmpeg(audio_bytes, n_semitones):
    """使用 pydub/ffmpeg 調整音調 (Post-processing)"""
    if not HAS_PYDUB or not HAS_FFMPEG or n_semitones == 0:
        return audio_bytes
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        # 簡單變調算法 (改變採樣率) - 會有"花栗鼠"效應 (Chipmunk effect) 但最穩定
        # 如果需要保持時長的變調，需要更復雜的 DSP
        new_sample_rate = int(audio.frame_rate * (2.0 ** (n_semitones / 12.0)))
        pitched = audio._spawn(audio.raw_data, overrides={'frame_rate': new_sample_rate})
        pitched = pitched.set_frame_rate(audio.frame_rate)
        
        out = io.BytesIO()
        pitched.export(out, format="mp3")
        return out.getvalue()
    except:
        return audio_bytes

# --- 6. Piper 模型管理 ---
MODELS_DIR = Path("piper_models")
MODELS_DIR.mkdir(exist_ok=True)

def download_file(url, local_path):
    """直接使用 requests 下載文件，避免 huggingface_hub 的認證問題"""
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        if os.path.exists(local_path):
            os.remove(local_path) # 清理失敗的文件
        raise e

def get_piper_model_path(model_key):
    """確保模型存在，若無則下載"""
    if not HAS_PIPER: return None, None
    
    config = PIPER_MODELS[model_key]
    onnx_path = MODELS_DIR / f"{model_key}.onnx"
    json_path = MODELS_DIR / f"{model_key}.onnx.json"
    
    if not onnx_path.exists() or not json_path.exists():
        with st.spinner(f"正在下載 Piper 模型 {config['name']} (首次運行需時較長)..."):
            try:
                # 構建直接下載 URL
                # 格式: https://huggingface.co/datasets/{repo_id}/resolve/main/{path}
                base_url = f"https://huggingface.co/datasets/{config['repo']}/resolve/main"
                
                url_onnx = f"{base_url}/{config['file_onnx']}"
                url_json = f"{base_url}/{config['file_json']}"
                
                download_file(url_onnx, onnx_path)
                download_file(url_json, json_path)
                
            except Exception as e:
                st.error(f"模型下載失敗: {e}")
                return None, None

    return str(onnx_path), str(json_path)

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

def generate_audio_stream_piper(text, model_key, speed_slider, noise_scale, pitch_semitones, remove_silence=False, silence_threshold=-70.0):
    """
    speed_slider: -100 (Slow) to 100 (Fast).
    Piper length_scale: >1 Slow, <1 Fast. Default 1.0.
    """
    if not HAS_PIPER: return b""
    
    onnx_path, json_path = get_piper_model_path(model_key)
    if not onnx_path: return b""

    # Map Slider (-100 to 100) to Piper Length Scale (0.5 to 2.0 approx)
    # Slider 0 = 1.0
    # Slider 100 (Fast) = 0.6 (Short duration)
    # Slider -100 (Slow) = 1.5 (Long duration)
    if speed_slider >= 0:
        # Fast: 1.0 -> 0.6
        length_scale = 1.0 - (speed_slider / 250.0) 
    else:
        # Slow: 1.0 -> 1.5
        length_scale = 1.0 + (abs(speed_slider) / 200.0)

    try:
        voice = PiperVoice.load(onnx_path, config_path=json_path)
        
        # Piper outputs raw 16-bit 22050Hz PCM usually
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wav_file:
            voice.synthesize(text, wav_file, length_scale=length_scale, noise_scale=noise_scale)
        
        # Convert Wav to MP3 using PyDub
        wav_io.seek(0)
        audio = AudioSegment.from_wav(wav_io)
        
        # Apply Pitch Shift (Post-processing)
        if pitch_semitones != 0:
             # Using the adjust function defined earlier (simple resampling)
             new_sample_rate = int(audio.frame_rate * (2.0 ** (pitch_semitones / 12.0)))
             audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_sample_rate})
             audio = audio.set_frame_rate(22050) # Reset to standard

        out_mp3 = io.BytesIO()
        audio.export(out_mp3, format="mp3")
        final_bytes = out_mp3.getvalue()
        
        if remove_silence:
            final_bytes = trim_silence(final_bytes, silence_threshold)
        return final_bytes

    except Exception as e:
        print(f"Piper Error: {e}")
        return b""

# --- 7. 介面邏輯 ---
def main():
    with st.sidebar:
        st.markdown("## 參數設定")
        
        # 引擎選擇
        engine_options = ["Edge TTS (微軟/高音質)", "Google TTS (谷歌/標準)"]
        if HAS_PIPER and HAS_FFMPEG:
             engine_options.append("Piper TTS (本地/快速)")
        
        engine = st.radio("TTS 引擎庫", engine_options, label_visibility="collapsed")
        
        # 參數變數初始化
        selected_voice = None
        selected_lang_code = None
        google_slow = False
        rate = 0
        pitch = 0
        volume = 0
        
        # Piper specific
        piper_model = None
        piper_noise = 0.667
        
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

        # --- PIPER TTS UI ---
        elif "Piper" in engine:
            st.markdown("### 1. 模型")
            st.info("Piper 為本地離線生成，速度極快。首次使用需下載模型。")
            c1, c2 = st.columns([1, 2])
            with c1: st.markdown('<div class="row-label">模型選擇</div>', unsafe_allow_html=True)
            with c2: 
                piper_model = st.selectbox("模型", list(PIPER_MODELS.keys()), format_func=lambda x: PIPER_MODELS[x]['name'], label_visibility="collapsed")
            
            st.markdown("### 2. 參數")
            # Reuse 'rate' variable for Piper Speed mapping
            rate = st.slider("語速 (Speed)", -100, 100, 0, format="%d%%", help="控制發音長度 (Length Scale)")
            # Reuse 'pitch' variable for Semitones
            pitch = st.slider("音調 (Pitch)", -12, 12, 0, format="%d", help="後處理變調 (Semitones)。注意：會改變音色。")
            piper_noise = st.slider("語氣變化 (Noise)", 0.1, 1.0, 0.667, step=0.01, help="控制語音的隨機變化程度 (Noise Scale)")

        st.markdown("---")
        remove_silence_opt = st.checkbox("智能去靜音", value=True, disabled=not(HAS_PYDUB and HAS_FFMPEG))
        silence_threshold = -70
        if remove_silence_opt:
            silence_threshold = st.slider("靜音判定閾值 (dB)", -80, -10, -70, step=5)
        
        # Status Bar
        if HAS_PYDUB and HAS_FFMPEG:
            status_html = '<div class="status-ok"><span>●</span> 環境完整'
            if HAS_PIPER: status_html += ' (+Piper)'
            status_html += '</div>'
            st.markdown(status_html, unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-err"><span>○</span> 環境缺失 (需 ffmpeg)</div>', unsafe_allow_html=True)
        st.markdown("<div style='text-align: center; color: #a1a1aa; font-size: 10px; font-family: monospace;'>VERSION 1.1.0 / TRI-ENGINE</div>", unsafe_allow_html=True)

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
                        data = asyncio.run(generate_audio_stream_edge(txt, selected_voice, rate, volume, pitch, remove_silence_opt, silence_threshold))
                    elif "Google" in engine:
                        data = generate_audio_stream_google(txt, selected_lang_code, google_slow, remove_silence_opt, silence_threshold)
                    elif "Piper" in engine:
                        # Rate passed as slider value (-100 to 100), Pitch as semitones (-12 to 12)
                        data = generate_audio_stream_piper(txt, piper_model, rate, piper_noise, pitch, remove_silence_opt, silence_threshold)
                        
                    zf.writestr(f"{fname}.mp3", data)
                except Exception as e:
                    st.error(f"{fname} 失敗: {e}")
                prog.progress((i+1)/len(items))
        
        st.success("生成完成！")
        st.download_button("下載 ZIP 壓縮檔", zip_buffer.getvalue(), "audio.zip", "application/zip")

if __name__ == "__main__":
    main()