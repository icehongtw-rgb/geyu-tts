import { GoogleGenAI, Modality } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY || '' });

export interface GeminiTTSOptions {
  voice?: 'Puck' | 'Charon' | 'Kore' | 'Fenrir' | 'Zephyr';
  text: string;
}

/**
 * Generates speech using Gemini 3.1 Flash TTS.
 * Returns a base64 string of the audio data.
 */
export async function generateGeminiSpeech(options: GeminiTTSOptions): Promise<string> {
  const { voice = 'Kore', text } = options;
  
  try {
    const response = await ai.models.generateContent({
      model: "gemini-3.1-flash-tts-preview",
      contents: [{ parts: [{ text }] }],
      config: {
        responseModalities: [Modality.AUDIO],
        speechConfig: {
          voiceConfig: {
            prebuiltVoiceConfig: { voiceName: voice },
          },
        },
      },
    });

    const base64Audio = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
    if (!base64Audio) {
      throw new Error("No audio data returned from Gemini TTS");
    }

    return base64Audio;
  } catch (error) {
    console.error("Gemini TTS Error:", error);
    throw error;
  }
}
