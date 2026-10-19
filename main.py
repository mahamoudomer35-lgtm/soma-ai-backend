from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Soma AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xrhqfnvhktupekxffzuv.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "sb_publishable_lGcUO42DonOuwGMOWIZGgA_WXIjr95-")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not set.")

groq_client = Groq(api_key=GROQ_API_KEY)
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

class ChatRequest(BaseModel):
    message: str
    language: str = "en"

class ChatResponse(BaseModel):
    reply: str

@app.get("/")
def root():
    return {"status": "ok", "message": "Soma AI Backend is running"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    
    token = authorization.split(" ")[1]
    
    try:
        user_res = supabase_client.auth.get_user(token)
        if not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid user")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth failed: {str(e)}")

    sys_prompts = {
        "en": "You are Soma AI, a helpful AI assistant. Reply in English.",
        "ar": "أنت سوما الذكاء الاصطناعي، مساعد ذكي ومفيد. أجب باللغة العربية.",
        "so": "Waxaad tahay Soma AI. Ku jawaab afka Soomaaliga."
    }
    sys_prompt = sys_prompts.get(request.language, sys_prompts["en"])

    try:
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": request.message}
            ],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=1024,
        )
        return {"reply": completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI failed: {str(e)}")
