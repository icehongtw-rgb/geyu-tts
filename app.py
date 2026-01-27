import streamlit as st
import edge_tts
import asyncio
import zipfile
import io
import re
from xml.sax.saxutils import escape

# 嘗試導入 pydub，若失敗則標記不可用
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

# 設定頁面配置
st.set_page_config(
    page_title="格育 - 兒童語音合成工具 (Edge-TTS 專業版)",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS 美化 ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .main .block-container { padding-top: 2rem; }
    .stTextArea textarea { font-family: monospace; border-radius: 0.5rem; }
    div[data-testid="stExpander"] div[role="button"] p { font-weight: bold; font-size: 1rem; }
    .stSelectbox div[data-baseweb="select"] > div:first-child {
        cursor: pointer;
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. 完整的 Edge-TTS 語音清單 ---
VOICES = {
    "繁體中文 (台灣)": {
        "zh-TW-HsiaoChenNeural": "🇹🇼 曉臻 (女聲 - 溫柔/標準/最常用)",
        "zh-TW-YunJheNeural": "🇹🇼 雲哲 (男聲 - 沉穩/標準)",
        "zh-TW-HsiaoYuNeural": "🇹🇼 曉雨 (女聲 - 清晰/可愛)",
    },
    "簡體中文 (中國 - 支援多情感)": {
        "zh-CN-XiaoxiaoNeural": "🇨🇳 小曉 (女聲 - 活潑/全能情感王)",
        "zh-CN-YunxiNeural": "🇨🇳 雲希 (男聲 - 帥氣/多情感)",
        "zh-CN-XiaoyiNeural": "🇨🇳 小藝 (女聲 - 氣質/多情感)",
        "zh-CN-YunjianNeural": "🇨🇳 雲健 (男聲 - 體育/廣播)",
        "zh-CN-YunyangNeural": "🇨🇳 雲陽 (男聲 - 新聞/專業)",
        "zh-CN-XiaohanNeural": "🇨🇳 曉涵 (女聲 - 溫暖/講故事)",
        "zh-CN-Liaoning-XiaobeiNeural": "🇨🇳 小北 (東北口音 - 有趣)",
        "zh-CN-sichuan-YunxiNeural": "🇨🇳 雲希 (四川話)",
        "zh-CN-shaanxi-XiaoniNeural": "🇨🇳 小妮 (陝西話)",
    },
    "英文 (美國 - 支援多情感)": {
        "en-US-AriaNeural": "🇺🇸 Aria (女聲 - 美式標準/多情感)",
        "en-US-GuyNeural": "🇺🇸 Guy (男聲 - 美式標準)",
        "en-US-AnaNeural": "🇺🇸 Ana (女聲 - 兒童/可愛)",
        "en-US-ChristopherNeural": "🇺🇸 Christopher (男聲 - 優雅)",
        "en-US-EricNeural": "🇺🇸 Eric (男聲 - 年輕)",
        "en-US-MichelleNeural": "🇺🇸 Michelle (女聲 - 專業)",
        "en-US-RogerNeural": "🇺🇸 Roger (男聲 - 還有點像聖誕老人)",
    },
    "英文 (英國)": {
        "en-GB-SoniaNeural": "🇬🇧 Sonia (女聲 - 英式標準)",
        "en-GB-RyanNeural": "🇬🇧 Ryan (男聲 - 英式標準)",
        "en-GB-MaisieNeural": "🇬🇧 Maisie (女聲 - 兒童)",
    },
    "其他語言 (精選)": {
        "ja-JP-NanamiNeural": "🇯🇵 Nanami (日語 - 女聲)",
        "ja-JP-KeitaNeural": "🇯🇵 Keita (日語 - 男聲)",
        "ko-KR-SunHiNeural": "🇰🇷 SunHi (韓語 - 女聲)",
        "ko-KR-InJoonNeural": "🇰🇷 InJoon (韓語 - 男聲)",
    }
}

# --- 2. 哪些角色支援 Style (白名單) ---
VOICES_WITH_STYLE = [
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-YunxiNeural",
    "zh-CN-XiaoyiNeural",
    "zh-CN-YunyangNeural",
    "zh-CN-XiaohanNeural",
    "en-US-AriaNeural",
    "en-US-GuyNeural",
    "en-US-JennyNeural",
    "en-US-DavisNeural"
]

# --- 3. 完整情感風格清單 ---
STYLES = {
    "general": "預設 (General)",
    "affectionate": "親切/哄孩子 (Affectionate) - 適合講睡前故事",
    "gentle": "溫柔 (Gentle) - 適合引導/療癒",
    "cheerful": "開心 (Cheerful)",
    "sad": "悲傷 (Sad)",
    "angry": "生氣 (Angry)",
    "fearful": "恐懼 (Fearful)",
    "calm": "冷靜 (Calm)",
    "serious": "嚴肅 (Serious)",
    "disgruntled": "不滿/抱怨 (Disgruntled)",
    "lyrical": "抒情 (Lyrical) - 適合朗讀散文",
    "shouting": "大喊 (Shouting)",
    "whispering": "耳語/悄悄話 (Whispering)",
    "poetry-reading": "朗讀詩詞 (Poetry Reading)",
    "newscast": "新聞播報 (Newscast)",
    "customerservice": "客服語氣 (Customer Service)",
    "assistant": "語音助理 (Assistant)",
    "chat": "閒聊 (Chat)",
}

def trim_silence(audio_bytes, silence_thresh=-50.0, chunk_size=10):
    """
    使用 pydub 去除頭尾靜音
    """
    if not HAS_PYDUB:
        return audio_bytes, "未安裝 pydub (請重啟 App)"
    
    try:
        # 載入音訊
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        
        def detect_leading_silence(sound, silence_threshold=silence_thresh, chunk_size=chunk_size):
            trim_ms = 0
            while trim_ms < len(sound) and sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold:
                trim_ms += chunk_size
            return trim_ms

        start_trim = detect_leading_silence(audio)
        end_trim = detect_leading_silence(audio.reverse())
        
        duration = len(audio)
        # 避免切過頭
        if start_trim + end_trim >= duration:
            return audio_bytes, "靜音過多，保留原檔"
            
        trimmed_audio = audio[start_trim:duration-end_trim]
        
        # 匯出
        out_io = io.BytesIO()
        trimmed_audio.export(out_io, format="mp3")
        return out_io.getvalue(), None

    except Exception as e:
        # 通常是找不到 ffmpeg
        return audio_bytes, f"處理失敗 (可能未安裝 FFmpeg): {str(e)}"

async def generate_audio_stream(text, voice, rate, volume, pitch, style="general", remove_silence=False):
    """
    使用 edge-tts 生成音訊並返回 bytes。
    v1.9 fix: 強制單行 (One-Liner) + 雙引號 + xml:lang 確保格式絕對正確
    """
    
    # 策略 1: 安全模式 (Safe Mode) - 適用於預設風格
    if style == "general":
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        
    # 策略 2: 高級模式 (Advanced Mode) - 適用於特殊情感
    else:
        escaped_text = escape(text)
        
        # 動態提取語言代碼 (例如 zh-CN)
        try:
            lang_code = "-".join(voice.split("-")[:2])
        except:
            lang_code = "en-US"

        # 檢查參數是否有變動
        is_default_prosody = (rate == "+0%" and volume == "+0%" and pitch == "+0Hz")
        
        # 構建 Prosody 部分 (雙引號)
        if is_default_prosody:
            content_part = escaped_text
        else:
            content_part = f'<prosody rate="{rate}" volume="{volume}" pitch="{pitch}">{escaped_text}</prosody>'

        # v1.9 終極修正：將所有內容壓縮成一行，不使用換行符號
        # 並使用標準雙引號，這最符合 XML 規範，也能避免 Edge-TTS 誤判
        # 補回 xml:lang，但在某些環境下是必須的
        final_ssml = (
            f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{lang_code}">'
            f'<voice name="{voice}">'
            f'<mstts:express-as style="{style}">'
            f'{content_part}'
            f'</mstts:express-as>'
            f'</voice>'
            f'</speak>'
        )
        
        communicate = edge_tts.Communicate(final_ssml, voice)

    # --- 獲取原始音訊 ---
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
    
    raw_bytes = audio_data.getvalue()
    debug_info = communicate._text if hasattr(communicate, '_text') else "SSML Hidden"

    # --- 後製去除靜音 ---
    if remove_silence:
        processed_bytes, error_msg = trim_silence(raw_bytes)
        if error_msg:
            return processed_bytes, f"{debug_info}\n[Warning] 去除靜音失敗: {error_msg}"
        return processed_bytes, debug_info
            
    return raw_bytes, debug_info

def parse_input(text):
    items = []
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = re.match(r'^(\S+)\s+(.+)$', line)
        if match:
            filename_raw = match.group(1)
            content = match.group(2)
            filename = filename_raw.replace('.mp3', '').replace('.wav', '')
            items.append({"filename": filename, "text": content, "status": "pending"})
    return items

def main():
    with st.sidebar:
        st.title("⚙️ 參數設定")
        st.caption("版本：v1.9 (SSML 單行修正版)")
        
        # 顯示依賴庫狀態
        if HAS_PYDUB:
            st.caption("✅ Pydub: 已安裝")
        else:
            st.warning("⚠️ Pydub: 未安裝 (請 Reboot App)")

        st.subheader("1. 選擇聲音")
        category = st.selectbox("語言類別", options=list(VOICES.keys()), index=1)
        voice_options = VOICES[category]
        selected_voice_key = st.selectbox("語音角色", options=list(voice_options.keys()), format_func=lambda x: voice_options[x])

        st.subheader("2. 語音調整")
        speed_val = st.slider("語速 (Rate)", -50, 100, 0, format="%d%%", step=5)
        rate_str = f"{'+' if speed_val >= 0 else ''}{speed_val}%"
        
        vol_val = st.slider("音量 (Volume)", -50, 50, 0, format="%d%%", step=5)
        volume_str = f"{'+' if vol_val >= 0 else ''}{vol_val}%"
        
        pitch_val = st.slider("音調 (Pitch)", -50, 50, 0, format="%dHz", step=5)
        pitch_str = f"{'+' if pitch_val >= 0 else ''}{pitch_val}Hz"

        st.subheader("3. 進階 (Advanced)")
        supports_style = selected_voice_key in VOICES_WITH_STYLE
        
        if supports_style:
            st.success("✅ 此模型支援情感調整")
            selected_style_key = st.selectbox("情感風格 (Style)", options=list(STYLES.keys()), format_func=lambda x: STYLES[x], index=0)
        else:
            st.info("ℹ️ 此模型不支援情感調整")
            st.selectbox("情感風格 (Style)", options=["general"], format_func=lambda x: "預設 (General)", disabled=True)
            selected_style_key = "general"
        
        st.markdown("---")
        
        remove_silence_opt = st.checkbox("✨ 自動去除頭尾靜音", value=False, help="需系統安裝 FFmpeg。可去除音檔前後多餘的空白。")
        show_debug = st.checkbox("顯示 SSML (除錯用)", value=False)

    st.title("🧩 格育 - 兒童語音合成工具 (Edge-TTS)")
    st.markdown("使用微軟 **Edge-TTS** 引擎，完全免費、無額度限制，支援批量生成與自動命名。")

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📝 批量輸入內容")
        input_text = st.text_area(
            "請輸入內容 (每一行：檔名 [空白] 文字)",
            height=350,
            placeholder="001 蘋果\n002 香蕉\n1-1 這是第一課的內容\nintroduction Welcome to the class",
            help="系統會自動將第一段文字作為檔名 (例如 '001')，後面的文字作為內容。"
        )
        items = parse_input(input_text)
        
        if len(items) > 0:
            st.success(f"已偵測到 **{len(items)}** 個待處理項目")
            with st.expander("點擊預覽解析結果"):
                st.table(items[:5])
        else:
            st.info("👆 請在上方輸入框輸入文字以開始")

    with col2:
        st.markdown("### 🔊 試聽與測試")
        preview_text = st.text_area("測試語句", "這是一個語音測試，小朋友們好！", height=100)
        
        if st.button("生成試聽", use_container_width=True):
            if not preview_text:
                st.warning("請輸入測試文字")
            else:
                with st.spinner("生成中..."):
                    try:
                        audio_bytes, debug_info = asyncio.run(generate_audio_stream(
                            preview_text, selected_voice_key, rate_str, volume_str, pitch_str, selected_style_key, remove_silence_opt
                        ))
                        st.audio(audio_bytes, format="audio/mp3")
                        
                        # v1.9 Logic Fix: Always show debug if checked, even if there's a warning
                        if show_debug:
                            st.text_area("Debug Info (SSML)", debug_info, height=150)
                            
                        if "[Warning]" in str(debug_info):
                            st.warning(str(debug_info).split('\n')[-1])
                            
                    except Exception as e:
                        st.error(f"錯誤: {str(e)}")

    st.divider()

    if st.button("🚀 開始批量生成 (ZIP下載)", type="primary", use_container_width=True, disabled=len(items) == 0):
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_container = st.container()
        
        zip_buffer = io.BytesIO()
        success_count = 0
        fail_count = 0

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, item in enumerate(items):
                status_text.text(f"正在處理 ({i+1}/{len(items)}): {item['filename']}...")
                try:
                    audio_bytes, err_msg = asyncio.run(generate_audio_stream(
                        item['text'], selected_voice_key, rate_str, volume_str, pitch_str, selected_style_key, remove_silence_opt
                    ))
                    
                    if "[Warning]" in str(err_msg):
                         with log_container:
                            st.warning(f"⚠️ {item['filename']}: {str(err_msg).split('Warning] ')[-1]}")

                    file_name_in_zip = f"{item['filename']}.mp3"
                    zip_file.writestr(file_name_in_zip, audio_bytes)
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    with log_container:
                        st.error(f"❌ {item['filename']} 失敗: {str(e)}")
                progress_bar.progress((i + 1) / len(items))

        status_text.success(f"🎉 處理完成！成功: {success_count}, 失敗: {fail_count}")
        zip_buffer.seek(0)
        st.download_button(
            label=f"📥 下載 ZIP 壓縮檔 ({len(items)} 個檔案)",
            data=zip_buffer,
            file_name="GeYu_Batch_Audio.zip",
            mime="application/zip",
            type="primary"
        )

if __name__ == "__main__":
    main()
