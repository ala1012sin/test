from fastapi import APIRouter, Request
from typing import Dict, Any
from services.pinecone_service import PineconeService
from services.kakao_service import KakaoService
from .session import user_sessions

router = APIRouter(prefix="/kakao", tags=["kakao-recommend"])
pinecone = PineconeService()
kakao = KakaoService()

# 추천/검색 블록의 스킬 URL => /kakao/recommend 로 설정
@router.post("/recommend")
async def kakao_recommend(request: Request):
    body: Dict[str, Any] = await request.json()

    user_key = body.get("userRequest", {}).get("user", {}).get("id", "")
    utterance = body.get("userRequest", {}).get("utterance", "") or ""

    # 오픈빌더 params (sys_location, food, location) 
    params = body.get("action", {}).get("params", {}) or {}
    sys_location = params.get("sys_location")
    food = params.get("food")
    location = params.get("location")

    # 위치명 → 좌표
    geo = await kakao.geocode_landmark(location, sys_location)

    if geo:
        lat, lng = geo["lat"], geo["lng"]
        stores = await pinecone.search_stores_by_location(lat, lng, radius=5.0, top_k=5)
    else:
        # 텍스트 기반 백업 검색
        query = " ".join([x for x in [utterance, sys_location, location, food] if x])
        stores = await pinecone.search_stores_by_text(query, top_k=5)

    if not stores:
        return kakao.create_text_response("죄송합니다. 검색 결과가 없습니다.")

    # 세션에 결과 저장 (다음 상세보기 라우터에서 활용)
    user_sessions[user_key] = {
        "mode": "list",
        "stores": stores,
        "chat_history": []
    }

    # 추천 리스트: 버튼 blockId는 “가게정보조회(상세보기)” 블록 ID로 지정
    return kakao.create_list_card_response(stores)

