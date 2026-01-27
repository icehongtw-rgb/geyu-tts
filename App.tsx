import React, { useState, useEffect } from 'react';
import { Info, Bug, Scissors } from 'lucide-react';

// --- Data ported from app.py for accurate preview ---
const VOICES: Record<string, string[]> = {
    "繁體中文 (台灣)": [
        "🇹🇼 曉臻 (女聲 - 溫柔/標準/最常用)",
        "🇹🇼 雲哲 (男聲 - 沉穩/標準)",
        "🇹🇼 曉雨 (女聲 - 清晰/可愛)",
    ],
    "簡體中文 (中國 - 支援多情感)": [
        "🇨🇳 小曉 (女聲 - 活潑/全能情感王)",
        "🇨🇳 雲希 (男聲 - 帥氣/多情感)",
        "🇨🇳 小藝 (女聲 - 氣質/多情感)",
        "🇨🇳 雲健 (男聲 - 體育/廣播)",
        "🇨🇳 雲陽 (男聲 - 新聞/專業)",
        "🇨🇳 曉涵 (女聲 - 溫暖/講故事)",
        "🇨🇳 小北 (東北口音 - 有趣)",
        "🇨🇳 雲希 (四川話)",
        "🇨🇳 小妮 (陝西話)",
    ],
    "英文 (美國 - 支援多情感)": [
        "🇺🇸 Aria (女聲 - 美式標準/多情感)",
        "🇺🇸 Guy (男聲 - 美式標準)",
        "🇺🇸 Ana (女聲 - 兒童/可愛)",
        "🇺🇸 Christopher (男聲 - 優雅)",
        "🇺🇸 Eric (男聲 - 年輕)",
        "🇺🇸 Michelle (女聲 - 專業)",
        "🇺🇸 Roger (男聲 - 還有點像聖誕老人)",
    ],
    "英文 (英國)": [
        "🇬🇧 Sonia (女聲 - 英式標準)",
        "🇬🇧 Ryan (男聲 - 英式標準)",
        "🇬🇧 Maisie (女聲 - 兒童)",
    ],
    "其他語言 (精選)": [
        "🇯🇵 Nanami (日語 - 女聲)",
        "🇯🇵 Keita (日語 - 男聲)",
        "🇰🇷 SunHi (韓語 - 女聲)",
        "🇰🇷 InJoon (韓語 - 男聲)",
    ]
};

// Simplified check for preview purposes. 
// In python this checks exact IDs (zh-TW-...), here we check display strings.
// Xiaoxiao, Yunxi, Xiaoyi, Yunyang, Xiaohan, Aria, Guy
const VOICES_WITH_STYLE_KEYWORDS = [
    "小曉", "雲希", "小藝", "雲陽", "曉涵", "Aria", "Guy"
];

const STYLES = [
    "預設 (General)",
    "親切/哄孩子 (Affectionate)",
    "溫柔 (Gentle)",
    "開心 (Cheerful)",
    "悲傷 (Sad)",
    "生氣 (Angry)",
    "恐懼 (Fearful)",
    "冷靜 (Calm)",
    "嚴肅 (Serious)",
    "不滿/抱怨 (Disgruntled)",
    "抒情 (Lyrical)",
    "大喊 (Shouting)",
    "耳語/悄悄話 (Whispering)",
    "朗讀詩詞 (Poetry Reading)",
    "新聞播報 (Newscast)",
    "客服語氣 (Customer Service)",
    "語音助理 (Assistant)",
    "閒聊 (Chat)",
];

export default function StreamlitMock() {
  // Sync with app.py v1.2 defaults: Simplified Chinese & Xiaoxiao
  const [category, setCategory] = useState("簡體中文 (中國 - 支援多情感)");
  const [voice, setVoice] = useState(VOICES["簡體中文 (中國 - 支援多情感)"][0]);
  const [rate, setRate] = useState(0);
  const [volume, setVolume] = useState(0);
  const [pitch, setPitch] = useState(0);
  const [style, setStyle] = useState("預設 (General)");
  const [text, setText] = useState("");
  const [showDebug, setShowDebug] = useState(false);
  const [trimSilence, setTrimSilence] = useState(false);
  
  // Update voice when category changes
  useEffect(() => {
    // When switching categories, pick the first voice
    // If switching TO Simplified Chinese, ensure Xiaoxiao (index 0) is picked
    if (VOICES[category]) {
        setVoice(VOICES[category][0]);
    }
  }, [category]);

  // Logic: Check if current voice supports style
  const supportsStyle = VOICES_WITH_STYLE_KEYWORDS.some(keyword => voice.includes(keyword));

  // Auto-reset style if not supported (Visual only logic)
  useEffect(() => {
    if (!supportsStyle) {
        setStyle("預設 (General)");
    }
  }, [voice, supportsStyle]);

  return (
    <div className="min-h-screen bg-[#f8fafc] flex font-sans text-[#31333F]">
      {/* Sidebar Mock */}
      <div className="w-[21rem] bg-white border-r border-slate-200 p-6 flex flex-col gap-6 shrink-0 overflow-y-auto h-screen sticky top-0 hidden md:flex">
        <div className="space-y-4">
            <h2 className="text-xl font-bold flex items-center gap-2">
                ⚙️ 參數設定
            </h2>
            {/* Added Version Label */}
            <p className="text-xs text-slate-500 -mt-2">版本：v1.9 (SSML 單行修正版)</p>
            
            <div className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-600">1. 選擇聲音</h3>
                <div className="space-y-1">
                    <p className="text-xs text-slate-500">語言類別</p>
                    <select 
                        value={category}
                        onChange={(e) => setCategory(e.target.value)}
                        className="w-full p-2 border border-gray-300 rounded bg-white text-sm focus:ring-1 focus:ring-red-500 outline-none cursor-pointer"
                    >
                        {Object.keys(VOICES).map(cat => (
                            <option key={cat} value={cat}>{cat}</option>
                        ))}
                    </select>
                </div>
                <div className="space-y-1">
                    <p className="text-xs text-slate-500">語音角色</p>
                    <select 
                        value={voice}
                        onChange={(e) => setVoice(e.target.value)}
                        className="w-full p-2 border border-gray-300 rounded bg-white text-sm focus:ring-1 focus:ring-red-500 outline-none cursor-pointer"
                    >
                        {VOICES[category].map(v => (
                            <option key={v} value={v}>{v}</option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="space-y-4 pt-2">
                <h3 className="text-sm font-semibold text-slate-600">2. 語音調整</h3>
                
                <div>
                    <div className="flex justify-between text-xs mb-1">
                        <span>語速 (Rate)</span>
                        <span>{rate > 0 ? '+' : ''}{rate}%</span>
                    </div>
                    <input type="range" min="-50" max="100" value={rate} onChange={e => setRate(Number(e.target.value))} className="w-full accent-[#ff4b4b] h-1 bg-slate-200 rounded-lg cursor-pointer" />
                </div>
                
                <div>
                    <div className="flex justify-between text-xs mb-1">
                        <span>音量 (Volume)</span>
                        <span>{volume > 0 ? '+' : ''}{volume}%</span>
                    </div>
                    <input type="range" min="-50" max="50" value={volume} onChange={e => setVolume(Number(e.target.value))} className="w-full accent-[#ff4b4b] h-1 bg-slate-200 rounded-lg cursor-pointer" />
                </div>

                <div>
                    <div className="flex justify-between text-xs mb-1">
                        <span>音調 (Pitch)</span>
                        <span>{pitch > 0 ? '+' : ''}{pitch}Hz</span>
                    </div>
                    <input type="range" min="-50" max="50" value={pitch} onChange={e => setPitch(Number(e.target.value))} className="w-full accent-[#ff4b4b] h-1 bg-slate-200 rounded-lg cursor-pointer" />
                </div>
            </div>

            <div className="space-y-2 pt-2">
                <h3 className="text-sm font-semibold text-slate-600">3. 進階 (Advanced)</h3>
                
                {supportsStyle ? (
                    <>
                        <div className="bg-green-50 text-green-700 px-3 py-2 rounded text-sm flex items-center gap-2 border border-green-200">
                            <span>✅</span> 此模型支援情感調整
                        </div>
                        <select 
                            className="w-full p-2 border border-gray-300 rounded bg-white text-sm outline-none cursor-pointer"
                            value={style}
                            onChange={(e) => setStyle(e.target.value)}
                        >
                            {STYLES.map(s => (
                                <option key={s} value={s}>{s}</option>
                            ))}
                        </select>
                    </>
                ) : (
                    <>
                        <div className="bg-blue-50 text-blue-700 px-3 py-2 rounded text-sm flex items-center gap-2 border border-blue-200">
                            <span>ℹ️</span> 此模型不支援情感調整 (已鎖定)
                        </div>
                        <select 
                            className="w-full p-2 border border-gray-300 rounded bg-slate-100 text-slate-500 text-sm outline-none cursor-not-allowed"
                            value="預設 (General)"
                            disabled
                        >
                            <option>預設 (General)</option>
                        </select>
                    </>
                )}
            </div>
            
            <hr className="border-slate-100" />
            
            <div className="space-y-2">
                <div className="flex items-center gap-2">
                    <input 
                        type="checkbox" 
                        id="trim" 
                        checked={trimSilence} 
                        onChange={e => setTrimSilence(e.target.checked)}
                        className="w-4 h-4 accent-[#ff4b4b]"
                    />
                    <label htmlFor="trim" className="text-xs text-slate-700 cursor-pointer select-none flex items-center gap-1">
                        <Scissors className="w-3 h-3" /> ✨ 自動去除頭尾靜音
                    </label>
                </div>
                
                <div className="flex items-center gap-2">
                    <input 
                        type="checkbox" 
                        id="debug" 
                        checked={showDebug} 
                        onChange={e => setShowDebug(e.target.checked)}
                        className="w-4 h-4 accent-[#ff4b4b]"
                    />
                    <label htmlFor="debug" className="text-xs text-slate-700 cursor-pointer select-none">顯示 SSML (除錯用)</label>
                </div>
            </div>
            <p className="text-xs text-slate-500 mt-1">若遇到 'speak version...' 朗讀問題，請開啟此選項並截圖回報。</p>
        </div>
      </div>

      {/* Main Content Mock */}
      <div className="flex-1 p-8 md:p-12 max-w-5xl mx-auto space-y-8 overflow-y-auto">
        <header className="space-y-2">
            <h1 className="text-3xl md:text-4xl font-bold text-[#1e293b]">🧩 格育 - 兒童語音合成工具 (Edge-TTS)</h1>
            <div className="text-slate-600">
                使用微軟 <strong>Edge-TTS</strong> 引擎，完全免費、無額度限制，支援批量生成與自動命名。
            </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-2">
                <h3 className="text-lg font-semibold">📝 批量輸入內容</h3>
                <div className="relative">
                    <textarea 
                        className="w-full h-80 p-3 border border-slate-200 rounded-lg font-mono text-sm focus:border-[#ff4b4b] focus:ring-1 focus:ring-[#ff4b4b] outline-none resize-none shadow-sm"
                        placeholder={`001 蘋果\n002 香蕉\n1-1 這是第一課的內容\nintroduction Welcome to the class`}
                        value={text}
                        onChange={e => setText(e.target.value)}
                    ></textarea>
                    <div className="absolute bottom-3 right-3 text-xs text-slate-400">Press Ctrl+Enter to apply</div>
                </div>
                {text && (
                   <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-md text-sm flex items-center gap-2">
                      <span>✅</span> 已偵測到 <strong>{text.split('\n').filter(x=>x.trim()).length}</strong> 個待處理項目
                   </div>
                )}
                {!text && (
                    <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-md text-sm flex items-center gap-2">
                        <Info className="w-4 h-4" /> 👆 請在上方輸入框輸入文字以開始
                    </div>
                )}
            </div>

            <div className="space-y-4">
                <h3 className="text-lg font-semibold">🔊 試聽與測試</h3>
                <div className="space-y-2">
                    <label className="text-xs text-slate-600">測試語句</label>
                    <textarea 
                        className="w-full h-24 p-2 border border-slate-200 rounded-md text-sm outline-none resize-none shadow-sm"
                        defaultValue="這是一個語音測試，小朋友們好！"
                    ></textarea>
                </div>
                <button className="w-full py-2 bg-white border border-slate-200 hover:border-[#ff4b4b] hover:text-[#ff4b4b] text-slate-700 rounded transition-colors text-sm font-medium shadow-sm">
                    生成試聽
                </button>
                
                {showDebug && style !== "預設 (General)" && (
                     <div className="space-y-1">
                        <label className="text-xs text-slate-600 font-semibold flex items-center gap-1">
                             <Bug className="w-3 h-3"/> Debug SSML
                        </label>
                        <textarea 
                            className="w-full h-24 p-2 border border-slate-200 bg-slate-50 text-xs font-mono rounded-md outline-none resize-none shadow-sm"
                            readOnly
                            value={`<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='zh-CN'><voice name='zh-CN-XiaoxiaoNeural'><mstts:express-as xmlns:mstts='https://www.w3.org/2001/mstts' style='cheerful'>...</mstts:express-as></voice></speak>`}
                        ></textarea>
                     </div>
                )}
            </div>
        </div>

        <hr className="border-slate-200" />

        <button 
            disabled={!text}
            className={`w-full py-3 rounded-lg font-semibold text-white transition-all shadow-sm ${
                text 
                ? 'bg-[#ff4b4b] hover:bg-[#ff3333] shadow-lg shadow-red-100' 
                : 'bg-slate-200 cursor-not-allowed text-slate-400'
            }`}
        >
            🚀 開始批量生成 (ZIP下載)
        </button>

        {/* Floating Note */}
        <div className="fixed bottom-4 right-4 bg-yellow-50 border border-yellow-200 text-yellow-800 p-4 rounded-lg shadow-xl max-w-sm text-sm z-50">
            <strong className="block mb-1 text-yellow-900">⚠️ 這是預覽模式 (Preview Mode)</strong>
            <p className="leading-relaxed text-yellow-700">
                這是 <code>app.py</code> 的介面模擬。
                請將 <code>app.py</code> 和 <code>requirements.txt</code> 
                複製到 GitHub 並使用 Streamlit Cloud 部署以獲得完整功能。
            </p>
        </div>
      </div>
    </div>
  );
}