import React, { useState, useEffect } from 'react';
import { Info, Sliders, Scissors, Terminal, Zap, Server, HardDrive, Play, Download, Loader2, Volume2 } from 'lucide-react';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import { generateGeminiSpeech } from './services/geminiService';

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

// Google TTS Languages
const GOOGLE_LANGS: Record<string, string> = {
    "簡體中文 (zh-cn)": "zh-cn",
    "繁體中文 (zh-tw)": "zh-tw",
    "英文 (en)": "en"
};

const GEMINI_PROMPTS: Record<string, string> = {
    "none": "",
    "game": "用充滿活力、興奮且鼓勵的語氣對小朋友說：",
    "card": "以標準、清晰且溫柔的發音方式，像百科全書一樣朗讀：",
    "story": "用溫柔、親切且像是在講故事的口吻，慢慢地說：",
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
  const [engine, setEngine] = useState<"edge" | "google" | "gemini">("edge");
  
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

  // Gemini State
  const [geminiVoice, setGeminiVoice] = useState<'Puck' | 'Charon' | 'Kore' | 'Fenrir' | 'Zephyr'>('Kore');
  const [geminiPromptKey, setGeminiPromptKey] = useState<string>("none");

  // Shared State
  const [text, setText] = useState("");
  const [trimSilence, setTrimSilence] = useState(true);
  const [silenceThreshold, setSilenceThreshold] = useState(-70);
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);

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

  const wrapWavHeader = (pcmData: Uint8Array, sampleRate: number = 24000) => {
    const buffer = new ArrayBuffer(44 + pcmData.length);
    const view = new DataView(buffer);

    // RIFF identifier
    view.setUint8(0, 'R'.charCodeAt(0));
    view.setUint8(1, 'I'.charCodeAt(0));
    view.setUint8(2, 'F'.charCodeAt(0));
    view.setUint8(3, 'F'.charCodeAt(0));
    // file length
    view.setUint32(4, 36 + pcmData.length, true);
    // RIFF type
    view.setUint8(8, 'W'.charCodeAt(0));
    view.setUint8(9, 'A'.charCodeAt(0));
    view.setUint8(10, 'V'.charCodeAt(0));
    view.setUint8(11, 'E'.charCodeAt(0));
    // format chunk identifier
    view.setUint8(12, 'f'.charCodeAt(0));
    view.setUint8(13, 'm'.charCodeAt(0));
    view.setUint8(14, 't'.charCodeAt(0));
    view.setUint8(15, ' '.charCodeAt(0));
    // format chunk length
    view.setUint32(16, 16, true);
    // sample format (1 is PCM)
    view.setUint16(20, 1, true);
    // channel count
    view.setUint16(22, 1, true);
    // sample rate
    view.setUint32(24, sampleRate, true);
    // byte rate (sampleRate * channelCount * bitsPerSample / 8)
    view.setUint32(28, sampleRate * 2, true);
    // block align (channelCount * bitsPerSample / 8)
    view.setUint16(32, 2, true);
    // bits per sample
    view.setUint16(34, 16, true);
    // data chunk identifier
    view.setUint8(36, 'd'.charCodeAt(0));
    view.setUint8(37, 'a'.charCodeAt(0));
    view.setUint8(38, 't'.charCodeAt(0));
    view.setUint8(39, 'a'.charCodeAt(0));
    // data chunk length
    view.setUint32(40, pcmData.length, true);

    // write PCM data
    const pcmDataView = new Uint8Array(buffer, 44);
    pcmDataView.set(pcmData);

    return new Blob([buffer], { type: 'audio/wav' });
  };

  const handleBatchGenerate = async () => {
    if (!text) return;
    setIsGenerating(true);
    setProgress(0);

    const zip = new JSZip();
    const lines = text.split('\n').filter(l => l.trim());
    const total = lines.length;

    try {
      for (let i = 0; i < total; i++) {
        const line = lines[i].trim();
        const parts = line.split(/\s+/, 2);
        let id = `item_${i + 1}`;
        let content = line;

        if (parts.length >= 2) {
          id = parts[0];
          content = parts[1];
        }

        if (engine === 'gemini') {
          const fullText = geminiPromptKey !== 'none' ? `${GEMINI_PROMPTS[geminiPromptKey]}${content}` : content;
          const base64 = await generateGeminiSpeech({
            text: fullText,
            voice: geminiVoice
          });
          
          const binary = atob(base64);
          const bytes = new Uint8Array(binary.length);
          for (let j = 0; j < binary.length; j++) {
            bytes[j] = binary.charCodeAt(j);
          }
          
          // Gemini returns raw PCM 16-bit 24kHz
          const wavBlob = wrapWavHeader(bytes, 24000);
          
          // Use ArrayBuffer for zip.file to be more robust
          const arrayBuffer = await wavBlob.arrayBuffer();
          zip.file(`${id}.wav`, arrayBuffer);
        } else {
          // Placeholder for other engines if they need backend interaction
          // For now, we'll only fully implement Gemini in the React frontend
          // since the others usually require Python/FFMPEG backend
          console.warn(`Engine ${engine} is not fully implemented in the frontend yet.`);
          // To give a good experience, let's at least show it's "coming soon" or similar
          // Or just skip for now and focus on Gemini which is the user request.
        }

        setProgress(((i + 1) / total) * 100);
      }

      if (engine === 'gemini') {
          const content = await zip.generateAsync({ type: 'blob' });
          saveAs(content, `geyu_voice_gemini_${Date.now()}.zip`);
      } else {
          alert("目前 React 版本僅完整支援 Gemini TTS。Edge/Google/Piper 正在遷移中，請使用原始 Python 版本或等待更新。");
      }
    } catch (error) {
      console.error("Batch generate error:", error);
      alert("生成過程中發生錯誤，請檢查主控台。");
    } finally {
      setIsGenerating(false);
      setProgress(0);
    }
  };

  return (
    <div className="min-h-screen bg-[#fafafa] flex font-sans text-zinc-800 selection:bg-red-100 selection:text-red-900">
      {/* Sidebar Mock - Compact Mode */}
      <div className="w-[26rem] bg-white border-r border-zinc-100 p-5 flex flex-col shrink-0 h-screen sticky top-0 hidden md:flex">
        
        {/* Top Section: Title & Controls */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            <div>
                <h2 className="text-xl font-bold flex items-center gap-2 text-zinc-900 tracking-tight mb-2">
                    參數設定
                </h2>
            </div>
            
            {/* Engine Selection - Now with Piper */}
            <div className="space-y-2">
                <div className="flex gap-1 p-1 bg-zinc-100/50 rounded-lg border border-zinc-200">
                    <button 
                        onClick={() => setEngine("edge")}
                        className={`flex-1 py-1.5 px-2 text-[10px] font-bold rounded-md border transition-all ${engine === 'edge' ? 'bg-white text-red-600 border-zinc-200 shadow-sm' : 'bg-transparent text-zinc-500 border-transparent hover:text-zinc-700'}`}
                    >
                        Edge TTS
                    </button>
                    <button 
                        onClick={() => setEngine("google")}
                        className={`flex-1 py-1.5 px-2 text-[10px] font-bold rounded-md border transition-all ${engine === 'google' ? 'bg-white text-red-600 border-zinc-200 shadow-sm' : 'bg-transparent text-zinc-500 border-transparent hover:text-zinc-700'}`}
                    >
                        Google TTS
                    </button>
                    <button 
                        onClick={() => setEngine("gemini")}
                        className={`flex-1 py-1.5 px-2 text-[10px] font-bold rounded-md border transition-all ${engine === 'gemini' ? 'bg-white text-red-600 border-zinc-200 shadow-sm' : 'bg-transparent text-zinc-500 border-transparent hover:text-zinc-700'}`}
                    >
                        Gemini
                    </button>
                </div>
            </div>

            {/* --- Conditional Render: Edge TTS --- */}
            {engine === 'edge' && (
                <>
                    <div className="space-y-3 pt-3 border-t border-zinc-100">
                        <div className="space-y-2">
                            <div className="flex items-center justify-between gap-3">
                                <label className="text-sm font-medium text-zinc-700 whitespace-nowrap min-w-[4rem]">語言區域</label>
                                <select 
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                    className="flex-1 p-1.5 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none transition-shadow cursor-pointer hover:border-zinc-300"
                                >
                                    {Object.keys(EDGE_VOICES).map(cat => (
                                        <option key={cat} value={cat}>{cat}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="flex items-center justify-between gap-3">
                                <label className="text-sm font-medium text-zinc-700 whitespace-nowrap min-w-[4rem]">語音角色</label>
                                <select 
                                    value={voice}
                                    onChange={(e) => setVoice(e.target.value)}
                                    className="flex-1 p-1.5 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none transition-shadow cursor-pointer hover:border-zinc-300"
                                >
                                    {EDGE_VOICES[category].map(v => (
                                        <option key={v} value={v}>{v}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-3 pt-3 border-t border-zinc-100">
                        <div className="flex items-center justify-between gap-3">
                            <label className="text-sm font-medium text-zinc-700 whitespace-nowrap min-w-[4rem]">情感預設</label>
                            <select 
                                className="flex-1 p-1.5 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none cursor-pointer hover:border-zinc-300"
                                value={styleKey}
                                onChange={(e) => handleStyleChange(e.target.value)}
                            >
                                {Object.entries(STYLE_PRESETS).map(([key, config]) => (
                                    <option key={key} value={key}>{config.label}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <div className="space-y-4 pt-3 border-t border-zinc-100">
                        <div className="space-y-3">
                            <div className="group">
                                <div className="flex justify-between text-xs mb-1 text-zinc-600">
                                    <span className="font-medium">語速 Rate</span>
                                    <span className="font-mono bg-red-50 px-1.5 py-0.5 rounded text-[10px] text-red-600">{rate > 0 ? '+' : ''}{rate}%</span>
                                </div>
                                <input 
                                    type="range" min="-100" max="100" 
                                    value={rate} 
                                    onChange={e => { setRate(Number(e.target.value)); setStyleKey('custom'); }} 
                                    className="w-full h-1 bg-zinc-200 rounded-full appearance-none cursor-pointer accent-red-500 hover:accent-red-600" 
                                />
                            </div>
                            
                            <div className="group">
                                <div className="flex justify-between text-xs mb-1 text-zinc-600">
                                    <span className="font-medium">音調 Pitch</span>
                                    <span className="font-mono bg-red-50 px-1.5 py-0.5 rounded text-[10px] text-red-600">{pitch > 0 ? '+' : ''}{pitch}Hz</span>
                                </div>
                                <input 
                                    type="range" min="-100" max="100" 
                                    value={pitch} 
                                    onChange={e => { setPitch(Number(e.target.value)); setStyleKey('custom'); }} 
                                    className="w-full h-1 bg-zinc-200 rounded-full appearance-none cursor-pointer accent-red-500 hover:accent-red-600" 
                                />
                            </div>

                            <div className="group">
                                <div className="flex justify-between text-xs mb-1 text-zinc-600">
                                    <span className="font-medium">音量 Volume</span>
                                    <span className="font-mono bg-red-50 px-1.5 py-0.5 rounded text-[10px] text-red-600">{volume > 0 ? '+' : ''}{volume}%</span>
                                </div>
                                <input 
                                    type="range" min="-50" max="50" 
                                    value={volume} 
                                    onChange={e => setVolume(Number(e.target.value))} 
                                    className="w-full h-1 bg-zinc-200 rounded-full appearance-none cursor-pointer accent-red-500 hover:accent-red-600" 
                                />
                            </div>
                        </div>
                    </div>
                </>
            )}

            {/* --- Conditional Render: Google TTS --- */}
            {engine === 'google' && (
                <div className="space-y-4 pt-3 border-t border-zinc-100">
                     <div className="bg-zinc-50 border border-zinc-200 rounded-md p-2 text-xs text-zinc-500 leading-relaxed">
                        <span className="font-bold text-zinc-700 block mb-1">關於 Google TTS</span>
                        完全免費且穩定，但語音較為機械化。
                    </div>

                    <div className="flex items-center justify-between gap-3">
                        <label className="text-sm font-medium text-zinc-700 whitespace-nowrap min-w-[4rem]">語言選擇</label>
                        <select 
                            value={googleLang}
                            onChange={(e) => setGoogleLang(e.target.value)}
                            className="flex-1 p-1.5 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none transition-shadow cursor-pointer hover:border-zinc-300"
                        >
                            {Object.keys(GOOGLE_LANGS).map(l => (
                                <option key={l} value={l}>{l}</option>
                            ))}
                        </select>
                    </div>

                    <div className="pt-1">
                        <label className="flex items-center gap-3 p-2 rounded-lg border border-transparent hover:bg-zinc-50 hover:border-zinc-100 transition-all cursor-pointer group">
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

             {/* --- Conditional Render: Gemini TTS --- */}
             {engine === 'gemini' && (
                <div className="space-y-4 pt-3 border-t border-zinc-100">
                     <div className="bg-red-50 border border-red-100 rounded-md p-2 text-xs text-red-800 leading-relaxed shadow-sm">
                        <span className="font-bold block mb-1">New! Gemini 3.1 TTS</span>
                        <p>支援 70+ 語言。目前提供 5 種核心音色。</p>
                        <p className="mt-1 font-medium text-red-600">💡 提示：在文字前加上「用傷心的語氣說：」等指令，AI 會自動調整情感！</p>
                    </div>

                    <div className="flex items-center justify-between gap-3">
                        <label className="text-sm font-medium text-zinc-700 whitespace-nowrap min-w-[4rem]">語音角色</label>
                        <select 
                            value={geminiVoice}
                            onChange={(e) => setGeminiVoice(e.target.value as any)}
                            className="flex-1 p-1.5 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none transition-shadow cursor-pointer hover:border-zinc-300"
                        >
                            <option value="Kore">👩 Kore (女聲 - 平衡專業/推薦) ✨</option>
                            <option value="Puck">👧 Puck (女聲 - 活力稚嫩)</option>
                            <option value="Charon">👨 Charon (男聲 - 沉穩冷靜)</option>
                            <option value="Fenrir">🧔 Fenrir (男聲 - 神秘低沉)</option>
                            <option value="Zephyr">👩 Zephyr (女聲 - 明亮輕快)</option>
                        </select>
                    </div>

                    <div className="flex items-center justify-between gap-3">
                        <label className="text-sm font-medium text-zinc-700 whitespace-nowrap min-w-[4rem]">場景語氣</label>
                        <select 
                            value={geminiPromptKey}
                            onChange={(e) => setGeminiPromptKey(e.target.value)}
                            className="flex-1 p-1.5 border border-zinc-200 rounded-lg bg-white text-sm focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none transition-shadow cursor-pointer hover:border-zinc-300"
                        >
                            <option value="none">預設內容 (無指令)</option>
                            <option value="game">🎮 遊戲玩法 (充滿活力)</option>
                            <option value="card">📚 專業圖卡 (清晰播音)</option>
                            <option value="story">📖 親切故事 (溫柔緩慢)</option>
                        </select>
                    </div>
                </div>
            )}
            
            <div className="pt-3 border-t border-zinc-100 space-y-3">
                <label className="flex items-center gap-3 p-2 rounded-lg border border-transparent hover:bg-zinc-50 hover:border-zinc-100 transition-all cursor-pointer group">
                    <input 
                        type="checkbox" 
                        checked={trimSilence} 
                        onChange={e => setTrimSilence(e.target.checked)}
                        className="w-4 h-4 accent-red-500 rounded border-zinc-300 focus:ring-red-500"
                    />
                    <div className="flex flex-col">
                        <span className="text-sm font-medium text-zinc-700 group-hover:text-black">智能去靜音</span>
                        <span className="text-[10px] text-zinc-400">移除音檔前後空白</span>
                    </div>
                </label>

                {trimSilence && (
                    <div className="px-2 pb-1">
                         <div className="flex justify-between text-xs mb-1 text-zinc-600">
                            <span className="font-medium">靜音閾值</span>
                            <span className="font-mono bg-zinc-100 px-1.5 py-0.5 rounded text-[10px] text-zinc-500">{silenceThreshold}dB</span>
                        </div>
                        <input 
                            type="range" min="-80" max="-10" step="5"
                            value={silenceThreshold} 
                            onChange={e => setSilenceThreshold(Number(e.target.value))} 
                            className="w-full h-1 bg-zinc-200 rounded-full appearance-none cursor-pointer accent-red-500 hover:accent-red-600" 
                        />
                    </div>
                )}
            </div>
        </div>

        {/* Bottom Section: Status & Version */}
        <div className="mt-auto pt-4 border-t border-zinc-100 space-y-3 bg-white">
            {/* Status Badge */}
            <div className="bg-zinc-50 border border-zinc-200 text-zinc-600 px-3 py-2 rounded-md text-xs flex items-center gap-2 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                <span>Python 環境完整</span>
            </div>
            
            <p className="text-[10px] text-zinc-400 font-mono tracking-wide text-center">
                VERSION 1.1.0 / TRI-ENGINE
            </p>
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
                                {engine === 'edge' ? 'edge-tts' : (engine === 'gemini' ? 'gemini-tts' : 'google-tts')}
                            </span>
                         </div>
                         <code className="block font-mono text-xs text-zinc-300 leading-loose whitespace-pre-wrap break-all">
                            {engine === 'edge' ? (
                                <>
                                    <span className="text-zinc-500">voice:</span> <span className="text-white">"{voice.split(' ')[0]}"</span><br/>
                                    <span className="text-zinc-500">rate:</span> <span className="text-white">"{rate > 0 ? '+' : ''}{rate}%"</span><br/>
                                    <span className="text-zinc-500">pitch:</span> <span className="text-white">"{pitch > 0 ? '+' : ''}{pitch}Hz"</span>
                                </>
                            ) : engine === 'gemini' ? (
                                <>
                                    <span className="text-zinc-500">api:</span> <span className="text-white">"gemini-3.1-flash"</span><br/>
                                    <span className="text-zinc-500">voice:</span> <span className="text-white">"{geminiVoice}"</span><br/>
                                    <span className="text-zinc-500">vibe:</span> <span className="text-white">"{geminiPromptKey !== 'none' ? geminiPromptKey : 'default'}"</span><br/>
                                    <span className="text-zinc-500">multimodal:</span> <span className="text-white">true</span>
                                </>
                            ) : (
                                <>
                                    <span className="text-zinc-500">lang:</span> <span className="text-white">"{GOOGLE_LANGS[googleLang]}"</span><br/>
                                    <span className="text-zinc-500">slow:</span> <span className="text-white">{googleSlow ? 'true' : 'false'}</span>
                                </>
                            )}
                            <br/>
                            {trimSilence && (
                                <>
                                    <span className="text-zinc-500">silence_thresh:</span> <span className="text-white">"{silenceThreshold}dB"</span>
                                </>
                            )}
                         </code>
                    </div>

                    <p className="text-xs text-zinc-500 leading-relaxed">
                        系統將自動為每一行文字生成獨立的音檔，並打包為 ZIP 下載。
                    </p>
                </div>

                <button 
                    disabled={!text || isGenerating}
                    onClick={handleBatchGenerate}
                    className={`w-full py-5 rounded-xl font-bold text-sm tracking-widest uppercase transition-all shadow-xl transform flex items-center justify-center gap-3 ${
                        (text && !isGenerating)
                        ? 'bg-red-500 text-white hover:bg-red-600 hover:-translate-y-1 hover:shadow-2xl hover:shadow-red-200' 
                        : 'bg-zinc-100 text-zinc-400 cursor-not-allowed shadow-none'
                    }`}
                >
                    {isGenerating ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin text-red-500" />
                            <span className="text-red-500">Generating ({Math.round(progress)}%)</span>
                        </>
                    ) : (
                        <>
                            <span>Start Batch Generation</span>
                            {text && <span className="bg-white/20 px-2 py-0.5 rounded text-[10px]">ZIP</span>}
                        </>
                    )}
                </button>
            </div>
        </div>
      </div>
    </div>
  );
}