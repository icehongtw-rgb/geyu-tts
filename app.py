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

# 檢查 FFmpeg
if shutil.which("ffmpeg"):
    HAS_FFMPEG = True

# 檢查 Pydub
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
    "簡體中文 (中國 - 支援多情感)": {
        "zh-CN-XiaoxiaoNeural": "🇨🇳 小曉 (女聲 - 活潑/推薦) 🔥",
        "zh-CN-YunxiNeural": "🇨🇳 雲希 (男聲 - 帥氣/多情感)",
        "zh-CN-XiaoyiNeural": "🇨🇳 小藝 (女聲 - 氣質)",
        "zh-CN-YunjianNeural": "🇨🇳 雲健 (男聲 - 體育)",
        "zh-CN-XiaohanNeural": "🇨🇳 曉涵 (女聲 - 溫暖/講故事)",
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

VOICES_WITH_STYLE = [
    "zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-XiaoyiNeural", "zh-CN-XiaohanNeural",
    "en-US-AriaNeural", "en-US-GuyNeural", "en-US-AnaNeural"
]

STYLES = {
    "general": "預設 (General)",
    "affectionate": "❤️ 親切/哄孩子 (Affectionate)",
    "cheerful": "😄 開心 (Cheerful)",
    "gentle": "☁️ 溫和 (Gentle)",
    "sad": "😢 悲傷 (Sad)",
    "angry": "😡 生氣 (Angry)",
    "whispering": "🤫 耳語 (Whispering)",
    "shouting": "📢 大喊 (Shouting)",
}

# --- 4. 輔助功能 ---
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

# --- 5. 核心生成邏輯 (v10.1: 修復語法錯誤) ---
async def generate_audio_stream(text, voice, rate, volume, pitch, style="general", remove_silence=False):
    debug_info = {"is_ssml": False, "raw_ssml": ""}
    
    # 策略 1: 一般模式
    if style == "general":
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
    
    # 策略 2: 風格模式 (標準 SSML 構建)
    else:
        escaped_text = escape(text)
        
        # 判斷是否需要 Prosody
        has_prosody = not (rate == "+0%" and volume == "+0%" and pitch == "+0Hz")
        
        # v10.1: 使用 zh-CN 並確保雙引號
        ssml_parts = [
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN">',
            f'<voice name="{voice}">',
            f'<mstts:express-as style="{style}">',
        ]
        
        if has_prosody:
            ssml_parts.append(f'<prosody rate="{rate}" volume="{volume}" pitch="{pitch}">')
            ssml_parts.append(escaped_text)
            ssml_parts.append('</prosody>')
        else:
            ssml_parts.append(escaped_text)
            
        ssml_parts.append('</mstts:express-as>')
        ssml_parts.append('</voice>')
        ssml_parts.append('</speak>')
        
        clean_ssml = "".join(ssml_parts)
        
        debug_info["is_ssml"] = True
        debug_info["raw_ssml"] = clean_ssml
        
        communicate = edge_tts.Communicate(clean_ssml, voice)

    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
    
    final_bytes = audio_data.getvalue()
    if remove_silence:
        final_bytes = trim_silence(final_bytes)
        
    return final_bytes, debug_info

# --- 6. 介面邏輯 ---
def main():
    with st.sidebar:
        st.title("⚙️ 參數設定")
        st.caption("版本：v10.1 (語法修復版)")
        
        if HAS_PYDUB and HAS_FFMPEG:
            st.markdown('<div class="status-ok">✅ 環境完整</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-err">⚠️ 環境缺失 (需 Python 3.11)</div>', unsafe_allow_html=True)

        st.subheader("1. 語音")
        category = st.selectbox("語言", list(VOICES.keys()))
        selected_voice = st.selectbox("角色", list(VOICES[category].keys()), format_func=lambda x: VOICES[category][x])

        st.subheader("2. 調整")
        rate = st.slider("語速", -50, 100, 0, format="%d%%")
        pitch = st.slider("音調", -50, 50, 0, format="%dHz")
        rate_str = f"{'+' if rate >= 0 else ''}{rate}%"
        pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
        vol_str = "+0%"

        st.subheader("3. 風格")
        if selected_voice in VOICES_WITH_STYLE:
            style = st.selectbox("情感", list(STYLES.keys()), format_func=lambda x: STYLES[x], index=1)
        else:
            style = "general"
            st.selectbox("情感", ["預設 (General)"], disabled=True)

        remove_silence_opt = st.checkbox("✨ 自動去靜音", value=True, disabled=not(HAS_PYDUB and HAS_FFMPEG))
        show_debug = st.checkbox("🔍 開啟 SSML 檢視", value=True)

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
                    data, dbg = asyncio.run(generate_audio_stream(test_txt, selected_voice, rate_str, vol_str, pitch_str, style, remove_silence_opt))
                    st.audio(data, format='audio/mp3')
                    if show_debug and dbg.get("is_ssml"):
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
        
        debug_container = st.expander("🔍 批量生成 SSML 檢查", expanded=show_debug)
        
        # v10.1 修復：加上了 with 語句結尾的冒號 :
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, (fname, txt) in enumerate(items):
                try:
                    data, dbg = asyncio.run(generate_audio_stream(txt, selected_voice, rate_str, vol_str, pitch_str, style, remove_silence_opt))
                    zf.writestr(f"{fname}.mp3", data)
                    
                    if show_debug and dbg.get("is_ssml") and i == 0:
                        with debug_container:
                            st.write(f"📝 範例檔案: {fname}")
                            st.code(dbg["raw_ssml"], language="xml")
                            
                except Exception as e:
                    st.error(f"{fname} 失敗: {e}")
                prog.progress((i+1)/len(items))
        st.success("完成！")
        st.download_button("📥 下載 ZIP", zip_buffer.getvalue(), "audio.zip", "application/zip")

if __name__ == "__main__":
    main()