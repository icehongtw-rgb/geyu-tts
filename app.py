import streamlit as st
import edge_tts
import asyncio
import zipfile
import io
import re
import shutil
import sys
from xml.sax.saxutils import escape

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

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .status-ok { background-color: #dcfce7; color: #166534; padding: 0.5rem; border-radius: 5px; margin-bottom: 10px; border: 1px solid #bbf7d0;}
    .status-err { background-color: #fee2e2; color: #991b1b; padding: 0.5rem; border-radius: 5px; margin-bottom: 10px; border: 1px solid #fecaca;}
    .debug-box { font-family: monospace; font-size: 0.8rem; background: #e2e8f0; padding: 5px; border-radius: 3px; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 語音清單 ---
VOICES = {
    "簡體中文 (中國)": {
        "zh-CN-XiaoxiaoNeural": "🇨🇳 小曉 (女聲 - 活潑/推薦) 🔥",
        "zh-CN-YunxiNeural": "🇨🇳 雲希 (男聲 - 帥氣)",
        "zh-CN-XiaoyiNeural": "🇨🇳 小藝 (女聲 - 氣質)",
        "zh-CN-YunjianNeural": "🇨🇳 雲健 (男聲 - 體育)",
        "zh-CN-XiaohanNeural": "🇨🇳 曉涵 (女聲 - 溫暖)",
    },
    "繁體中文 (台灣)": {
        "zh-TW-HsiaoChenNeural": "🇹🇼 曉臻 (女聲 - 溫柔/標準)",
        "zh-TW-YunJheNeural": "🇹🇼 雲哲 (男聲 - 沉穩)",
        "zh-TW-HsiaoYuNeural": "🇹🇼 曉雨 (女聲 - 清晰)",
    },
    "英文 (美國)": {
        "en-US-AnaNeural": "🇺🇸 Ana (女聲 - 兒童/可愛)",
        "en-US-AriaNeural": "🇺🇸 Aria (女聲 - 標準)",
        "en-US-GuyNeural": "🇺🇸 Guy (男聲 - 標準)",
    }
}

# --- 4. 風格模擬參數 (物理外掛) ---
# 這裡定義了每個風格對應的「語速」和「音調」偏移量
# 這種方式 100% 安全，因為它只使用了基礎的 prosody 標籤
STYLE_PARAMS = {
    "general":      {"rate": 0,   "pitch": 0},
    "affectionate": {"rate": -15, "pitch": -2}, # 哄孩子：慢一點，低沉溫柔
    "cheerful":     {"rate": 10,  "pitch": 3},  # 開心：快一點，高亢
    "gentle":       {"rate": -10, "pitch": 0},  # 溫和：稍慢，平穩
    "sad":          {"rate": -15, "pitch": -5}, # 悲傷：很慢，低沉
    "angry":        {"rate": 5,   "pitch": 5},  # 生氣：稍快，高亢
    "whispering":   {"rate": -20, "pitch": -5}, # 耳語：非常慢
    "shouting":     {"rate": 5,   "pitch": 8},  # 大喊：高音
}

STYLES = {
    "general": "預設 (General)",
    "affectionate": "❤️ 親切/哄孩子 (模擬)",
    "cheerful": "😄 開心 (模擬)",
    "gentle": "☁️ 溫和 (模擬)",
    "sad": "😢 悲傷 (模擬)",
    "angry": "😡 生氣 (模擬)",
    "whispering": "🤫 耳語 (模擬)",
    "shouting": "📢 大喊 (模擬)",
}

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

# --- 6. 核心生成邏輯 (v16.0: 物理模擬版) ---
async def generate_audio_stream(text, voice, user_rate, user_volume, user_pitch, style="general", remove_silence=False):
    # 1. 取得風格對應的物理參數
    style_settings = STYLE_PARAMS.get(style, STYLE_PARAMS["general"])
    
    # 2. 將「使用者設定」與「風格預設」相加
    # 例如：使用者設 +0%，風格是 -15%，結果就是 -15%
    final_rate_val = user_rate + style_settings["rate"]
    final_pitch_val = user_pitch + style_settings["pitch"]
    
    # 3. 轉成字串格式
    rate_str = f"{'+' if final_rate_val >= 0 else ''}{final_rate_val}%"
    pitch_str = f"{'+' if final_pitch_val >= 0 else ''}{final_pitch_val}Hz"
    volume_str = f"{'+' if user_volume >= 0 else ''}{user_volume}%"
    
    # 4. 構建最簡單、最穩定的 SSML (只用 voice 和 prosody)
    # 這裡完全棄用了 mstts:express-as，所以絕對不會有相容性問題
    escaped_text = escape(text)
    
    ssml_parts = [
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">',
        f'<voice name="{voice}">',
        f'<prosody rate="{rate_str}" volume="{volume_str}" pitch="{pitch_str}">',
        escaped_text,
        '</prosody>',
        '</voice>',
        '</speak>'
    ]
    
    clean_ssml = "".join(ssml_parts)
    
    # 傳送給 edge-tts
    communicate = edge_tts.Communicate(clean_ssml, voice)
    
    # 這裡可以保留，確保萬無一失
    if hasattr(communicate, "_ssml"): communicate._ssml = True
    if hasattr(communicate, "_text"): communicate._text = clean_ssml

    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
    
    final_bytes = audio_data.getvalue()
    
    # Debug info
    debug_info = {
        "style_applied": style,
        "final_rate": rate_str,
        "final_pitch": pitch_str,
        "raw_ssml": clean_ssml
    }

    if remove_silence:
        final_bytes = trim_silence(final_bytes)
        
    return final_bytes, debug_info

# --- 7. 介面邏輯 ---
def main():
    with st.sidebar:
        st.title("⚙️ 參數設定")
        st.caption("版本：v16.0 (物理模擬版)")
        
        if HAS_PYDUB and HAS_FFMPEG:
            st.markdown('<div class="status-ok">✅ 環境完整</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-err">⚠️ 環境缺失 (需 Python 3.11)</div>', unsafe_allow_html=True)

        st.subheader("1. 語音")
        category = st.selectbox("語言", list(VOICES.keys()))
        selected_voice = st.selectbox("角色", list(VOICES[category].keys()), format_func=lambda x: VOICES[category][x])

        st.subheader("2. 調整 (基礎)")
        # 這裡的數值會與風格疊加
        rate = st.slider("語速微調", -50, 50, 0, format="%d%%", help="此數值會疊加在風格預設值上")
        pitch = st.slider("音調微調", -50, 50, 0, format="%dHz", help="此數值會疊加在風格預設值上")
        volume = st.slider("音量", -50, 50, 0, format="%d%%")

        st.subheader("3. 風格 (模擬)")
        style = st.selectbox("情感預設", list(STYLES.keys()), format_func=lambda x: STYLES[x], index=0)
        
        if style != "general":
            p = STYLE_PARAMS[style]
            st.info(f"💡 目前風格設定：語速 {p['rate']}%, 音調 {p['pitch']}Hz")

        remove_silence_opt = st.checkbox("✨ 自動去靜音", value=True, disabled=not(HAS_PYDUB and HAS_FFMPEG))
        show_debug = st.checkbox("🔍 顯示參數詳情", value=False)

    st.title("🧩 格育 - 兒童語音工具")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        text_input = st.text_area("輸入內容", height=300, placeholder="001 蘋果\n002 香蕉")
    
    with col2:
        st.write("試聽區")
        test_txt = st.text_input("測試句", "小朋友好！")
        if st.button("生成試聽"):
            with st.spinner("生成中..."):
                try:
                    data, dbg = asyncio.run(generate_audio_stream(test_txt, selected_voice, rate, volume, pitch, style, remove_silence_opt))
                    st.audio(data, format='audio/mp3')
                    if show_debug:
                         st.write(f"最終參數: Rate={dbg['final_rate']}, Pitch={dbg['final_pitch']}")
                         st.code(dbg["raw_ssml"], language="xml")
                except Exception as e:
                    st.error(f"錯誤: {e}")

    items = []
    for line in text_input.split('\n'):
        if line.strip():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                items.append((parts[0], parts[1]))
    
    if st.button(f"🚀 批量生成 ({len(items)} 個檔案)", type="primary", disabled=len(items)==0):
        zip_buffer = io.BytesIO()
        prog = st.progress(0)
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, (fname, txt) in enumerate(items):
                try:
                    data, dbg = asyncio.run(generate_audio_stream(txt, selected_voice, rate, volume, pitch, style, remove_silence_opt))
                    zf.writestr(f"{fname}.mp3", data)
                except Exception as e:
                    st.error(f"{fname} 失敗: {e}")
                prog.progress((i+1)/len(items))
        st.success("完成！")
        st.download_button("📥 下載 ZIP", zip_buffer.getvalue(), "audio.zip", "application/zip")

if __name__ == "__main__":
    main()