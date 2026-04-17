import asyncio
import edge_tts

async def main():
    voices = await edge_tts.VoicesManager.create()
    zh_voices = voices.find(Locale="zh-CN")
    for v in zh_voices:
        print(f"{v['Name']} - {v['Gender']}")

if __name__ == "__main__":
    asyncio.run(main())
