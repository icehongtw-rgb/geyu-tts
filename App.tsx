import React, { useState, useEffect } from 'react';
import { Info, Sliders, Scissors, Terminal, Zap } from 'lucide-react';

// --- Data synchronized with app.py ---
// Reordered: Female voices first, then Male voices
const VOICES: Record<string, string[]> = {
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
  const [category, setCategory] = useState("簡體中文 (中國)");
  const [voice, setVoice] = useState(VOICES["簡體中文 (中國)"][0]);
  
  const [styleKey, setStyleKey] = useState("general");
  const [rate, setRate] = useState(0);
  const [volume, setVolume] = useState(0);
  const [pitch, setPitch] = useState(0);
  const [text, setText] = useState("");
  const [trimSilence, setTrimSilence] = useState(true);

  useEffect(() => {
    if (VOICES[category]) {
        setVoice(VOICES[category][0]);
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
    <div className="min-h-screen bg-[#fafafa] flex font-sans text-zinc-800 selection:bg-zinc-200">
      {/* Sidebar Mock - Minimalist Gray */}
      <div className="w-[24rem] bg-white border-r border-zinc-100 p-8 flex flex-col gap-8 shrink-0 overflow-y-auto h-screen sticky top-0 hidden md:flex">
        <div className="space-y-6">
            <div>
                <h2 className="text-xl font-bold flex items-center gap-2 text-zinc-900 tracking-tight">
                    參數設定
                </h2>
                <p className="text-xs text-zinc-400 mt-2 font-mono tracking-wide">VERSION 19.1 / MONOCHROME</p>
            </div>
            
            {/* Status Badge - Neutral Gray */}
            <div className="bg-zinc-50 border border-zinc-200 text-zinc-600 px-3 py-2.5 rounded-md text-xs flex items-center gap-2 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
                <span>Python 環境就緒</span>
            </div>

            <div className="space-y-4">
                <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Voice Selection</h3>
                <div className="space-y-3">
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-zinc-700">語言區域</label>
                        <select 
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                            className="w-full p-3 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-2 focus:ring-black focus:border-transparent outline-none transition-shadow appearance-none cursor-pointer hover:border-zinc-300"
                        >
                            {Object.keys(VOICES).map(cat => (
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
                                className="w-full p-3 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-2 focus:ring-black focus:border-transparent outline-none transition-shadow appearance-none cursor-pointer hover:border-zinc-300"
                            >
                                {VOICES[category].map(v => (
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
                        className="w-full p-3 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-2 focus:ring-black focus:border-transparent outline-none cursor-pointer hover:border-zinc-300"
                        value={styleKey}
                        onChange={(e) => handleStyleChange(e.target.value)}
                    >
                        {Object.entries(STYLE_PRESETS).map(([key, config]) => (
                            <option key={key} value={key}>{config.label}</option>
                        ))}
                    </select>
                    <p className="text-[10px] text-zinc-400 leading-normal">
                        透過物理模擬 (Physical Simulation) 自動調整語速與音調，適用於所有角色。
                    </p>
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
                            <span className="font-mono bg-zinc-100 px-1.5 py-0.5 rounded text-[10px] text-zinc-500">{rate > 0 ? '+' : ''}{rate}%</span>
                        </div>
                        <input 
                            type="range" min="-100" max="100" 
                            value={rate} 
                            onChange={e => { setRate(Number(e.target.value)); setStyleKey('custom'); }} 
                            className="w-full h-1.5 bg-zinc-200 rounded-full appearance-none cursor-pointer accent-black hover:accent-zinc-800" 
                        />
                    </div>
                    
                    <div className="group">
                        <div className="flex justify-between text-xs mb-2 text-zinc-600">
                            <span className="font-medium">音調 Pitch</span>
                            <span className="font-mono bg-zinc-100 px-1.5 py-0.5 rounded text-[10px] text-zinc-500">{pitch > 0 ? '+' : ''}{pitch}Hz</span>
                        </div>
                        <input 
                            type="range" min="-100" max="100" 
                            value={pitch} 
                            onChange={e => { setPitch(Number(e.target.value)); setStyleKey('custom'); }} 
                            className="w-full h-1.5 bg-zinc-200 rounded-full appearance-none cursor-pointer accent-black hover:accent-zinc-800" 
                        />
                    </div>

                    <div className="group">
                        <div className="flex justify-between text-xs mb-2 text-zinc-600">
                            <span className="font-medium">音量 Volume</span>
                            <span className="font-mono bg-zinc-100 px-1.5 py-0.5 rounded text-[10px] text-zinc-500">{volume > 0 ? '+' : ''}{volume}%</span>
                        </div>
                        <input 
                            type="range" min="-50" max="50" 
                            value={volume} 
                            onChange={e => setVolume(Number(e.target.value))} 
                            className="w-full h-1.5 bg-zinc-200 rounded-full appearance-none cursor-pointer accent-black hover:accent-zinc-800" 
                        />
                    </div>
                </div>
            </div>
            
            <div className="pt-2">
                <label className="flex items-center gap-3 p-3 rounded-lg border border-transparent hover:bg-zinc-50 hover:border-zinc-100 transition-all cursor-pointer group">
                    <input 
                        type="checkbox" 
                        checked={trimSilence} 
                        onChange={e => setTrimSilence(e.target.checked)}
                        className="w-4 h-4 accent-black rounded border-zinc-300 focus:ring-zinc-500"
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
                 <div className="bg-black text-white p-2 rounded-lg">
                    <Zap className="w-5 h-5" />
                 </div>
                 <span className="text-xs font-bold text-zinc-400 tracking-wider uppercase">Geyu Studio</span>
            </div>
            <h1 className="text-4xl md:text-5xl font-extrabold text-zinc-900 tracking-tight">
                兒童語音合成工具
            </h1>
            <p className="text-zinc-500 max-w-2xl text-lg font-light leading-relaxed">
                專為教材製作設計的批量生成引擎。
                <br/>
                簡單、高效、純淨。
            </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
            <div className="lg:col-span-8 space-y-6">
                <div className="flex justify-between items-end">
                    <h3 className="text-xl font-bold text-zinc-800 flex items-center gap-2">
                        輸入內容
                    </h3>
                    <span className="text-xs text-zinc-400 font-mono bg-zinc-100 px-2 py-1 rounded">Format: ID Content</span>
                </div>
                
                <div className="relative group">
                    <textarea 
                        className="w-full h-[500px] p-6 border border-zinc-200 rounded-xl font-mono text-sm leading-8 text-zinc-700 focus:border-black focus:ring-1 focus:ring-black outline-none resize-none shadow-sm transition-all bg-white placeholder:text-zinc-300"
                        placeholder={`001 蘋果\n002 香蕉\n1-1 這是第一課的內容\nintroduction Welcome to the class`}
                        value={text}
                        onChange={e => setText(e.target.value)}
                    ></textarea>
                    <div className="absolute bottom-6 right-6 text-xs bg-zinc-100 px-3 py-1.5 rounded-full text-zinc-500 font-medium font-mono pointer-events-none">
                        {text.split('\n').filter(x=>x.trim()).length} Lines
                    </div>
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
                            <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono">edge-tts params</span>
                         </div>
                         <code className="block font-mono text-xs text-zinc-300 leading-loose whitespace-pre-wrap break-all">
                            <span className="text-zinc-500">voice:</span> <span className="text-white">"{voice.split(' ')[0]}"</span><br/>
                            <span className="text-zinc-500">rate:</span> <span className="text-white">"{rate > 0 ? '+' : ''}{rate}%"</span><br/>
                            <span className="text-zinc-500">pitch:</span> <span className="text-white">"{pitch > 0 ? '+' : ''}{pitch}Hz"</span><br/>
                            <span className="text-zinc-500">volume:</span> <span className="text-white">"{volume > 0 ? '+' : ''}{volume}%"</span>
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
                        ? 'bg-black text-white hover:bg-zinc-900 hover:-translate-y-1 hover:shadow-2xl' 
                        : 'bg-zinc-100 text-zinc-400 cursor-not-allowed shadow-none'
                    }`}
                >
                    <span>Start Batch Generation</span>
                    {text && <span className="bg-white/20 px-2 py-0.5 rounded text-[10px]">ZIP</span>}
                </button>
            </div>
        </div>
      </div>
      
      {/* Floating Preview Warning - Minimalist */}
      <div className="fixed bottom-6 right-6 bg-white/80 backdrop-blur border border-zinc-200 p-4 rounded-lg shadow-2xl max-w-xs z-50">
         <div className="flex items-center gap-3">
            <div className="w-1.5 h-1.5 rounded-full bg-black animate-pulse"></div>
            <span className="text-xs font-mono text-zinc-500">UI Preview Mode</span>
         </div>
      </div>
    </div>
  );
}