import streamlit as st
import edge_tts
import asyncio
import zipfile
import io
import re
from xml.sax.saxutils import escape

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
# 注意：台灣語音 (zh-TW) 目前官方 API 並不支援 style 參數
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

# --- 3. 完整情感風格清單 (針對 Xiaoxiao 等高級模型) ---
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

async def generate_audio_stream(text, voice, rate, volume, pitch, style="general"):
    """
    使用 edge-tts 生成音訊並返回 bytes。
    """
    # 雙重保險：如果語音不在支援名單內，強制設為 general，避免 API 報錯
    if voice not in VOICES_WITH_STYLE:
        style = "general"

    # 判斷是否需要使用 SSML
    if style != "general":
        escaped_text = escape(text)
        ssml = (
            f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-US'>"
            f"<voice name='{voice}'>"
            f"<mstts:express-as style='{style}'>"
            f"<prosody rate='{rate}' volume='{volume}' pitch='{pitch}'>"
            f"{escaped_text}"
            f"</prosody>"
            f"</mstts:express-as>"
            f"</voice>"
            f"</speak>"
        )
        # 修正：當使用 SSML 時，不需傳入 rate/volume/pitch 參數，也不要傳 None，直接初始化即可
        communicate = edge_tts.Communicate(ssml, voice)
    else:
        # 一般模式 (純文字)
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)

    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
            
    return audio_data.getvalue()

def parse_input(text):
    """
    解析輸入文本
    格式：[檔名] [空白] [內容]
    """
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
            
            items.append({
                "filename": filename,
                "text": content,
                "status": "pending"
            })
    return items

def main():
    # --- 側邊欄：參數設定 ---
    with st.sidebar:
        st.title("⚙️ 參數設定")
        
        # 1. 語音模型選擇
        st.subheader("1. 選擇聲音")
        category = st.selectbox("語言類別", options=list(VOICES.keys()))
        voice_options = VOICES[category]
        selected_voice_key = st.selectbox(
            "語音角色",
            options=list(voice_options.keys()),
            format_func=lambda x: voice_options[x]
        )

        # 2. 語音細節調整
        st.subheader("2. 語音調整")
        
        speed_val = st.slider("語速 (Rate)", -50, 100, 0, format="%d%%", step=5)
        rate_str = f"{'+' if speed_val >= 0 else ''}{speed_val}%"
        
        vol_val = st.slider("音量 (Volume)", -50, 50, 0, format="%d%%", step=5)
        volume_str = f"{'+' if vol_val >= 0 else ''}{vol_val}%"
        
        pitch_val = st.slider("音調 (Pitch)", -50, 50, 0, format="%dHz", step=5)
        pitch_str = f"{'+' if pitch_val >= 0 else ''}{pitch_val}Hz"

        # 3. 進階功能 (邏輯修復版)
        st.subheader("3. 進階 (Advanced)")
        
        # 判斷當前角色是否支援 Style
        supports_style = selected_voice_key in VOICES_WITH_STYLE
        
        if supports_style:
            st.success("✅ 此模型支援情感調整")
            selected_style_key = st.selectbox(
                "情感風格 (Style)",
                options=list(STYLES.keys()),
                format_func=lambda x: STYLES[x],
                index=0
            )
        else:
            st.info("ℹ️ 此模型不支援情感調整 (已鎖定)")
            # 顯示一個禁用的選單，視覺上讓用戶知道不能選
            st.selectbox(
                "情感風格 (Style)",
                options=["general"],
                format_func=lambda x: "預設 (General)",
                disabled=True
            )
            selected_style_key = "general"
        
        st.markdown("---")
        st.caption("檔案格式：預設為 **MP3** (Edge-TTS 原生高音質)")

    # --- 主區域 ---
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
                if len(items) > 5:
                    st.caption("...以及其他項目")
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
                        audio_bytes = asyncio.run(generate_audio_stream(
                            preview_text, selected_voice_key, rate_str, volume_str, pitch_str, selected_style_key
                        ))
                        st.audio(audio_bytes, format="audio/mp3")
                    except Exception as e:
                        st.error(f"錯誤: {str(e)}")

    st.divider()

    # --- 批量生成區 ---
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
                    # 生成音訊
                    audio_bytes = asyncio.run(generate_audio_stream(
                        item['text'], selected_voice_key, rate_str, volume_str, pitch_str, selected_style_key
                    ))
                    
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
