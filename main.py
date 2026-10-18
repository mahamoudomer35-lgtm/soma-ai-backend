from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Soma AI Backend")

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Restrict this to your Netlify URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq and Supabase clients
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xrhqfnvhktupekxffzuv.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "sb_publishable_lGcUO42DonOuwGMOWIZGgA_WXIjr95-")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not set in environment variables.")

groq_client = Groq(api_key=GROQ_API_KEY)
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

class ChatRequest(BaseModel):
    message: str
    language: str = "en"

class ChatResponse(BaseModel):
    reply: str

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Soma AI Backend"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")
    
    token = authorization.split(" ")[1]
    
    # 1. Verify user with Supabase
    try:
        user_res = supabase_client.auth.get_user(token)
        if not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid user token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

    # 2. Call Groq API
    system_prompts = {
        "en": "You are Soma AI, a helpful, smart, and concise AI assistant. Reply in English.",
        "ar": "أنت سوما الذكاء الاصطناعي، مساعد ذكي ومفيد وموجز. أجب باللغة العربية.",
        "so": "Waxaad tahay Soma AI, kaaliye caqli badan oo faa'iido leh. Ku jawaab afka Soomaaliga."
    }
    sys_prompt = system_prompts.get(request.language, system_prompts["en"])

    try:
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": request.message}
            ],
            model="llama3-8b-8192", # or mixtral-8x7b-32768
            temperature=0.7,
            max_tokens=1024,
        )
        reply = completion.choices[0].message.content
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Generation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
