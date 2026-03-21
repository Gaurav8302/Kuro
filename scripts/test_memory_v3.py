import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO)
sys.path.insert(0, 'backend')

from memory.chat_manager_v3 import ChatManagerV3

async def test_memory_flow():
    cm = ChatManagerV3()
    user_id = "test_user_v3"
    session_id = "test_session_v3"
    
    print("--- FIRST MESSAGE ---")
    res1 = await cm.handle_chat(
        user_id=user_id,
        session_id=session_id,
        user_input="Hi, I am building a project called Kuro with FastAPI.",
        chat_history=[]
    )
    print("Response 1:", res1["response"])
    print("Intent 1:", res1["intent"])
    print("Memories 1:", res1["memories_used"])
    
    # Wait to allow background tasks to run (memory updater)
    await asyncio.sleep(2)
    
    print("\n--- SECOND MESSAGE ---")
    res2 = await cm.handle_chat(
        user_id=user_id,
        session_id=session_id,
        user_input="What did I say I was building?",
        chat_history=[{"role": "user", "content": "Hi, I am building a project called Kuro with FastAPI."}, {"role": "assistant", "content": res1["response"]}]
    )
    print("Response 2:", res2["response"])
    print("Intent 2:", res2["intent"])
    print("Memories 2:", res2["memories_used"])

if __name__ == "__main__":
    asyncio.run(test_memory_flow())
