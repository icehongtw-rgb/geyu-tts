import React, { useState, useEffect } from 'react';
import { Info, Sliders, Scissors, Terminal, Zap, Server } from 'lucide-react';

// --- Data synchronized with app.py ---

// Edge TTS Voices
const EDGE_VOICES: Record<string, string[]> = {
    "簡體中文 (中國)": [
        "🇨🇳 小曉 (女聲 - 活潑/推薦) 🔥",
        "🇨🇳 小藝 (女聲 - 氣質)",
        "🇨🇳 雲希 (男聲 - 帥氣)",
        "🇨🇳 雲健 (男聲 - 體育)",
        "🇨🇳 雲揚 (男聲 - 專業/播音)",
    ],
    "繁體中文 (台灣)": [
        "🇹🇼 曉臻 (女聲 - 溫柔/標準)",
        "🇹🇼 曉雨 (女聲 - 清晰)",
        "🇹🇼 雲哲 (男聲 - 沉穩)",
    ],
    "英文 (美國)": [
        "🇺🇸 Ana (女聲 - 兒童/可愛)",
        "🇺🇸 Aria (女聲 - 標準)",
        "🇺🇸 Guy (男聲 - 標準)",
    ]
};

// Google TTS Languages (Simpler)
const GOOGLE_LANGS: Record<string, string> = {
    "簡體中文 (zh-cn)": "zh-cn",
    "繁體中文 (zh-tw)": "zh-tw",
    "英文 (en)": "en"
};

const STYLE_PRESETS: Record<string, { rate: number; pitch: number; label: string }> = {
    "general":      { rate: 0,   pitch: 0,   label: "預設 (General)" },
    "affectionate": { rate: -25, pitch: -5,  label: "❤️ 親切/哄孩子" },
    "cheerful":     { rate: 15,  pitch: 5,   label: "😄 開心" },
    "gentle":       { rate: -10, pitch: -2,  label: "☁️ 溫和" },
    "sad":          { rate: -30, pitch: -8,  label: "😢 悲傷" },
    "angry":        { rate: 10,  pitch: 8,   label: "😡 生氣" },
    "whispering":   { rate: -30, pitch: -10, label: "🤫 耳語" },
    "shouting":     { rate: 10,  pitch: 12,  label: "📢 大喊" },
};

export default function StreamlitMock() {
  const [engine, setEngine] = useState<"edge" | "google">("edge");
  
  // Edge State
  const [category, setCategory] = useState("簡體中文 (中國)");
  const [voice, setVoice] = useState(EDGE_VOICES["簡體中文 (中國)"][0]);
  const [styleKey, setStyleKey] = useState("general");
  const [rate, setRate] = useState(0);
  const [volume, setVolume] = useState(0);
  const [pitch, setPitch] = useState(0);

  // Google State
  const [googleLang, setGoogleLang] = useState("簡體中文 (zh-cn)");
  const [googleSlow, setGoogleSlow] = useState(false);

  // Shared State
  const [text, setText] = useState("");
  const [trimSilence, setTrimSilence] = useState(true);

  useEffect(() => {
    if (EDGE_VOICES[category]) {
        setVoice(EDGE_VOICES[category][0]);
    }
  }, [category]);

  const handleStyleChange = (newStyleKey: string) => {
    setStyleKey(newStyleKey);
    const preset = STYLE_PRESETS[newStyleKey];
    if (preset) {
        setRate(preset.rate);
        setPitch(preset.pitch);
    }
  };

  return (
    <div className="min-h-screen bg-[#fafafa] flex font-sans text-zinc-800 selection:bg-red-100 selection:text-red-900">
      {/* Sidebar Mock - Minimalist Gray */}
      <div className="w-[24rem] bg-white border-r border-zinc-100 p-8 flex flex-col gap-8 shrink-0 overflow-y-auto h-screen sticky top-0 hidden md:flex">
        <div className="space-y-6">
            <div>
                <h2 className="text-xl font-bold flex items-center gap-2 text-zinc-900 tracking-tight">
                    參數設定
                </h2>
                <p className="text-xs text-zinc-400 mt-2 font-mono tracking-wide">VERSION 1.0 / DUAL ENGINE</p>
            </div>
            
            {/* Status Badge */}
            <div className="bg-zinc-50 border border-zinc-200 text-zinc-600 px-3 py-2.5 rounded-md text-xs flex items-center gap-2 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                <span>Python 環境就緒</span>
            </div>

            {/* Engine Selection */}
            <div className="space-y-2">
                <label className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
                    <Server className="w-3 h-3" /> TTS 引擎庫
                </label>
                <div className="flex gap-2">
                    <button 
                        onClick={() => setEngine("edge")}
                        className={`flex-1 py-2 px-3 text-xs font-bold rounded-lg border transition-all ${engine === 'edge' ? 'bg-red-50 text-red-600 border-red-200' : 'bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300'}`}
                    >
                        Edge TTS
                    </button>
                    <button 
                        onClick={() => setEngine("google")}
                        className={`flex-1 py-2 px-3 text-xs font-bold rounded-lg border transition-all ${engine === 'google' ? 'bg-red-50 text-red-600 border-red-200' : 'bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300'}`}
                    >
                        Google TTS
                    </button>
                </div>
            </div>

            {/* --- Conditional Render: Edge TTS --- */}
            {engine === 'edge' && (
                <>
                    <div className="space-y-4 pt-4 border-t border-zinc-100">
                        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Voice Selection</h3>
                        <div className="space-y-3">
                            <div className="space-y-1.5">
                                <label className="text-sm font-medium text-zinc-700">語言區域</label>
                                <select 
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                    className="w-full p-3 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none transition-shadow appearance-none cursor-pointer hover:border-zinc-300"
                                >
                                    {Object.keys(EDGE_VOICES).map(cat => (
                                        <option key={cat} value={cat}>{cat}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-sm font-medium text-zinc-700">語音角色</label>
                                <div className="relative">
                                    <select 
                                        value={voice}
                                        onChange={(e) => setVoice(e.target.value)}
                                        className="w-full p-3 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none transition-shadow appearance-none cursor-pointer hover:border-zinc-300"
                                    >
                                        {EDGE_VOICES[category].map(v => (
                                            <option key={v} value={v}>{v}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-4 pt-4 border-t border-zinc-100">
                        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex justify-between items-center">
                            Style & Tone
                        </h3>
                        
                        <div className="space-y-3">
                            <select 
                                className="w-full p-3 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none cursor-pointer hover:border-zinc-300"
                                value={styleKey}
                                onChange={(e) => handleStyleChange(e.target.value)}
                            >
                                {Object.entries(STYLE_PRESETS).map(([key, config]) => (
                                    <option key={key} value={key}>{config.label}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <div className="space-y-6 pt-4 border-t border-zinc-100">
                        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
                            Fine Tuning
                        </h3>
                        
                        <div className="space-y-5">
                            <div className="group">
                                <div className="flex justify-between text-xs mb-2 text-zinc-600">
                                    <span className="font-medium">語速 Rate</span>
                                    <span className="font-mono bg-red-50 px-1.5 py-0.5 rounded text-[10px] text-red-600">{rate > 0 ? '+' : ''}{rate}%</span>
                                </div>
                                <input 
                                    type="range" min="-100" max="100" 
                                    value={rate} 
                                    onChange={e => { setRate(Number(e.target.value)); setStyleKey('custom'); }} 
                                    className="w-full h-1.5 bg-zinc-200 rounded-full appearance-none cursor-pointer accent-red-500 hover:accent-red-600" 
                                />
                            </div>
                            
                            <div className="group">
                                <div className="flex justify-between text-xs mb-2 text-zinc-600">
                                    <span className="font-medium">音調 Pitch</span>
                                    <span className="font-mono bg-red-50 px-1.5 py-0.5 rounded text-[10px] text-red-600">{pitch > 0 ? '+' : ''}{pitch}Hz</span>
                                </div>
                                <input 
                                    type="range" min="-100" max="100" 
                                    value={pitch} 
                                    onChange={e => { setPitch(Number(e.target.value)); setStyleKey('custom'); }} 
                                    className="w-full h-1.5 bg-zinc-200 rounded-full appearance-none cursor-pointer accent-red-500 hover:accent-red-600" 
                                />
                            </div>

                            <div className="group">
                                <div className="flex justify-between text-xs mb-2 text-zinc-600">
                                    <span className="font-medium">音量 Volume</span>
                                    <span className="font-mono bg-red-50 px-1.5 py-0.5 rounded text-[10px] text-red-600">{volume > 0 ? '+' : ''}{volume}%</span>
                                </div>
                                <input 
                                    type="range" min="-50" max="50" 
                                    value={volume} 
                                    onChange={e => setVolume(Number(e.target.value))} 
                                    className="w-full h-1.5 bg-zinc-200 rounded-full appearance-none cursor-pointer accent-red-500 hover:accent-red-600" 
                                />
                            </div>
                        </div>
                    </div>
                </>
            )}

            {/* --- Conditional Render: Google TTS --- */}
            {engine === 'google' && (
                <div className="space-y-4 pt-4 border-t border-zinc-100">
                     <div className="bg-zinc-50 border border-zinc-200 rounded-md p-3 text-xs text-zinc-500 leading-relaxed">
                        <span className="font-bold text-zinc-700 block mb-1">關於 Google TTS</span>
                        完全免費且穩定，但語音較為機械化，且不支援語速（除慢速外）、音調與情感調整。
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-zinc-700">語言</label>
                        <select 
                            value={googleLang}
                            onChange={(e) => setGoogleLang(e.target.value)}
                            className="w-full p-3 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none transition-shadow appearance-none cursor-pointer hover:border-zinc-300"
                        >
                            {Object.keys(GOOGLE_LANGS).map(l => (
                                <option key={l} value={l}>{l}</option>
                            ))}
                        </select>
                    </div>

                    <div className="pt-2">
                        <label className="flex items-center gap-3 p-3 rounded-lg border border-transparent hover:bg-zinc-50 hover:border-zinc-100 transition-all cursor-pointer group">
                            <input 
                                type="checkbox" 
                                checked={googleSlow} 
                                onChange={e => setGoogleSlow(e.target.checked)}
                                className="w-4 h-4 accent-red-500 rounded border-zinc-300 focus:ring-red-500"
                            />
                            <div className="flex flex-col">
                                <span className="text-sm font-medium text-zinc-700 group-hover:text-black">慢速模式</span>
                                <span className="text-[10px] text-zinc-400">Slow Mode</span>
                            </div>
                        </label>
                    </div>
                </div>
            )}
            
            <div className="pt-4 border-t border-zinc-100">
                <label className="flex items-center gap-3 p-3 rounded-lg border border-transparent hover:bg-zinc-50 hover:border-zinc-100 transition-all cursor-pointer group">
                    <input 
                        type="checkbox" 
                        checked={trimSilence} 
                        onChange={e => setTrimSilence(e.target.checked)}
                        className="w-4 h-4 accent-red-500 rounded border-zinc-300 focus:ring-red-500"
                    />
                    <div className="flex flex-col">
                        <span className="text-sm font-medium text-zinc-700 group-hover:text-black">智能去靜音</span>
                        <span className="text-[10px] text-zinc-400">自動移除音檔前後的空白片段</span>
                    </div>
                </label>
            </div>
        </div>
      </div>

      {/* Main Content Mock */}
      <div className="flex-1 p-8 md:p-16 max-w-7xl mx-auto space-y-12 overflow-y-auto">
        <header className="space-y-4 pb-8 border-b border-zinc-100">
            <div className="flex items-center gap-3 mb-2">
                 <div className="bg-red-500 text-white p-2 rounded-lg shadow-sm shadow-red-200">
                    <Zap className="w-5 h-5" />
                 </div>
                 <span className="text-xs font-bold text-red-500 tracking-wider uppercase">Geyu Studio</span>
            </div>
            <h1 className="text-4xl md:text-5xl font-extrabold text-zinc-900 tracking-tight">
                兒童語音合成工具
            </h1>
            <p className="text-zinc-500 max-w-2xl text-lg font-light leading-relaxed">
                專為教材製作設計的批量生成引擎。
            </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
            <div className="lg:col-span-8 space-y-6">
                <div className="flex justify-between items-end">
                    <h3 className="text-xl font-bold text-zinc-800 flex items-center gap-2">
                        輸入內容
                    </h3>
                    <span className="text-xs text-red-600 font-mono bg-red-50 px-2 py-1 rounded border border-red-100">Format: ID Content</span>
                </div>
                
                <div className="relative group">
                    <textarea 
                        className="w-full h-[500px] p-6 border border-zinc-200 rounded-xl font-mono text-sm leading-8 text-zinc-700 focus:border-red-500 focus:ring-1 focus:ring-red-500 outline-none resize-none shadow-sm transition-all bg-white placeholder:text-zinc-300"
                        placeholder={`001 蘋果\n002 香蕉\n1-1 這是第一課的內容\nintroduction Welcome to the class`}
                        value={text}
                        onChange={e => setText(e.target.value)}
                    ></textarea>
                </div>
                
                {!text && (
                    <div className="flex items-center gap-4 text-zinc-400 p-2">
                        <Info className="w-4 h-4" />
                        <span className="text-sm">請輸入文字以啟用生成功能。支援多行批量處理。</span>
                    </div>
                )}
            </div>

            <div className="lg:col-span-4 space-y-8">
                <div className="bg-white p-6 rounded-2xl border border-zinc-100 shadow-sm space-y-6">
                    <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-widest flex items-center gap-2">
                        Preview Config
                    </h3>
                    
                    <div className="bg-zinc-900 rounded-lg p-4 overflow-hidden shadow-inner">
                         <div className="flex items-center gap-2 border-b border-zinc-800 pb-3 mb-3">
                            <Terminal className="w-3.5 h-3.5 text-zinc-500" />
                            <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono">
                                {engine === 'edge' ? 'edge-tts' : 'google-tts'}
                            </span>
                         </div>
                         <code className="block font-mono text-xs text-zinc-300 leading-loose whitespace-pre-wrap break-all">
                            {engine === 'edge' ? (
                                <>
                                    <span className="text-zinc-500">voice:</span> <span className="text-white">"{voice.split(' ')[0]}"</span><br/>
                                    <span className="text-zinc-500">rate:</span> <span className="text-white">"{rate > 0 ? '+' : ''}{rate}%"</span><br/>
                                    <span className="text-zinc-500">pitch:</span> <span className="text-white">"{pitch > 0 ? '+' : ''}{pitch}Hz"</span>
                                </>
                            ) : (
                                <>
                                    <span className="text-zinc-500">lang:</span> <span className="text-white">"{GOOGLE_LANGS[googleLang]}"</span><br/>
                                    <span className="text-zinc-500">slow:</span> <span className="text-white">{googleSlow ? 'true' : 'false'}</span>
                                </>
                            )}
                         </code>
                    </div>

                    <p className="text-xs text-zinc-500 leading-relaxed">
                        系統將自動為每一行文字生成獨立的 MP3 檔案，並打包為 ZIP 下載。
                    </p>
                </div>

                <button 
                    disabled={!text}
                    className={`w-full py-5 rounded-xl font-bold text-sm tracking-widest uppercase transition-all shadow-xl transform flex items-center justify-center gap-3 ${
                        text 
                        ? 'bg-red-500 text-white hover:bg-red-600 hover:-translate-y-1 hover:shadow-2xl hover:shadow-red-200' 
                        : 'bg-zinc-100 text-zinc-400 cursor-not-allowed shadow-none'
                    }`}
                >
                    <span>Start Batch Generation</span>
                    {text && <span className="bg-white/20 px-2 py-0.5 rounded text-[10px]">ZIP</span>}
                </button>
            </div>
        </div>
      </div>
    </div>
  );
}