import streamlit as st
import edge_tts
import asyncio
import zipfile
import io
import re
import shutil
import sys
from xml.sax.saxutils import escape

# --- 1. 環境檢測 (Pydub & FFmpeg) ---
HAS_FFMPEG = False
HAS_PYDUB = False
PYDUB_STATUS = "Checking..."

# 檢查 FFmpeg (系統層級)
if shutil.which("ffmpeg"):
    HAS_FFMPEG = True
else:
    HAS_FFMPEG = False

# 檢查 Pydub (Python 層級)
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
    PYDUB_STATUS = "Installed"
except ImportError:
    HAS_PYDUB = False
    PYDUB_STATUS = "Not Found"

# --- 2. 設定頁面 ---
st.set_page_config(page_title="格育 - 兒童語音合成工具", page_icon="🧩", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .status-ok { background-color: #dcfce7; color: #166534; padding: 0.5rem; border-radius: 5px; margin-bottom: 10px; border: 1px solid #bbf7d0;}
    .status-err { background-color: #fee2e2; color: #991b1b; padding: 0.5rem; border-radius: 5px; margin-bottom: 10px; border: 1px solid #fecaca;}
    </style>
""", unsafe_allow_html=True)

# --- 3. 語音與風格清單 ---
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

# --- 4. 去除靜音功能 ---
def trim_silence(audio_bytes):
    if not HAS_PYDUB or not HAS_FFMPEG:
        return audio_bytes 

    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        
        def detect_leading(sound, silence_threshold=-50.0, chunk_size=10):
            trim_ms = 0
            while trim_ms < len(sound) and sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold:
                trim_ms += chunk_size
            return trim_ms

        start_trim = detect_leading(audio)
        end_trim = detect_leading(audio.reverse())
        
        # 只要切掉的長度小於總長度，就執行裁切
        if start_trim + end_trim < len(audio):
            trimmed = audio[start_trim:len(audio)-end_trim]
            out = io.BytesIO()
            trimmed.export(out, format="mp3")
            return out.getvalue()
    except Exception:
        pass 
    
    return audio_bytes

# --- 5. 核心生成邏輯 (雙引號 SSML 修復版) ---
async def generate_audio_stream(text, voice, rate, volume, pitch, style="general", remove_silence=False):
    # 如果選擇了風格，必須使用 SSML
    if style != "general":
        escaped_text = escape(text)
        
        # 【關鍵修復】
        # 1. 這裡全部使用雙引號 " 來包住屬性
        # 2. 移除了 xml:lang 防止與 voice 衝突
        # 3. 結構緊湊，沒有多餘換行
        ssml = (
            f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts">'
            f'<voice name="{voice}">'
            f'<mstts:express-as style="{style}">'
            f'<prosody rate="{rate}" volume="{volume}" pitch="{pitch}">'
            f'{escaped_text}'
            f'</prosody>'
            f'</mstts:express-as>'
            f'</voice>'
            f'</speak>'
        )
        communicate = edge_tts.Communicate(ssml, voice)
    else:
        # 一般模式 (無 SSML)
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)

    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
    
    final_bytes = audio_data.getvalue()

    if remove_silence:
        final_bytes = trim_silence(final_bytes)
        
    return final_bytes

# --- 6. 介面邏輯 ---
def main():
    with st.sidebar:
        st.title("⚙️ 參數設定")
        st.caption("版本：v3.1 (Python 3.11 適配版)")
        
        # 環境診斷顯示
        if HAS_PYDUB and HAS_FFMPEG:
            st.markdown('<div class="status-ok">✅ 環境完整：自動去靜音功能已就緒</div>', unsafe_allow_html=True)
        else:
            missing = []
            if not HAS_PYDUB: missing.append("Pydub (請在 Streamlit 設定將 Python 改為 3.11)")
            if not HAS_FFMPEG: missing.append("FFmpeg (檢查 packages.txt)")
            error_msg = "<br>".join(missing)
            st.markdown(f'<div class="status-err">⚠️ 環境缺失：<br>{error_msg}</div>', unsafe_allow_html=True)

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
        # 智慧判斷是否顯示風格
        if selected_voice in VOICES_WITH_STYLE:
            style = st.selectbox("情感", list(STYLES.keys()), format_func=lambda x: STYLES[x], index=1)
        else:
            style = "general"
            st.selectbox("情感", ["預設 (General)"], disabled=True, help="此角色不支援情感調整")
            if "zh-TW" in selected_voice:
                st.caption("ℹ️ 台灣語音暫不支援情感，建議調整語速與音調來模擬。")

        # 自動勾選去靜音 (如果是可用狀態)
        remove_silence_opt = st.checkbox("✨ 自動去除頭尾靜音", value=True, disabled=not(HAS_PYDUB and HAS_FFMPEG))

    st.title("🧩 格育 - 兒童語音工具")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        text_input = st.text_area("輸入內容 (編號 內容)", height=300, placeholder="001 蘋果\n002 香蕉")
    
    with col2:
        st.write("試聽")
        test_txt = st.text_input("測試句", "小朋友好！")
        if st.button("生成試聽"):
            with st.spinner("生成中..."):
                try:
                    data = asyncio.run(generate_audio_stream(test_txt, selected_voice, rate_str, vol_str, pitch_str, style, remove_silence_opt))
                    st.audio(data, format='audio/mp3')
                except Exception as e:
                    st.error(f"錯誤: {e}")

    items = []
    for line in text_input.split('\n'):
        if line.strip():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                items.append((parts[0], parts[1]))
    
    if st.button(f"🚀 批量生成 ({len(items)} 個檔案)", type="primary", disabled=len(items)==0):
        zip_buf = io.BytesIO()
        prog = st.progress(0)
        
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for i, (fname, txt) in enumerate(items):
                try:
                    data = asyncio.run(generate_audio_stream(txt, selected_voice, rate_str, vol_str, pitch_str, style, remove_silence_opt))
                    zf.writestr(f"{fname}.mp3", data)
                except Exception as e:
                    st.error(f"{fname} 失敗: {e}")
                prog.progress((i+1)/len(items))
        
        st.success("完成！")
        st.download_button("📥 下載 ZIP", zip_buf.getvalue(), "audio.zip", "application/zip")

if __name__ == "__main__":
    main()