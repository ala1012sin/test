from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import kakao_webhook
from routers import kakao_store
from routers import kakao_recommend
import uvicorn

app = FastAPI(
    title="Restaurant Chatbot API",
    description="카카오톡 맛집 추천 챗봇 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(kakao_webhook.router)
app.include_router(kakao_store.router)
app.include_router(kakao_recommend.router)

@app.get("/")
async def root():
    return {
        "message": "Restaurant Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "kakao_webhook": "/kakao/webhook",
            "kakao_webhook": "/kakao/store",
            "kakao_webhook": "/kakao/recommend",
            "health": "/kakao/health"
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
