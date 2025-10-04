from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
from services.pinecone_service import PineconeService
from services.openai_service import OpenAIService
from services.kakao_service import KakaoService

router = APIRouter(prefix="/kakao", tags=["kakao"])
pinecone_service = PineconeService()
openai_service = OpenAIService()
kakao_service = KakaoService()

# 세션 관리 (실제로는 Redis 등 사용 권장)
user_sessions = {}

@router.post("/webhook")
async def kakao_webhook(request: Request):
    """카카오톡 챗봇 웹훅"""
    try:
        body = await request.json()
        
        # 카카오톡 요청 파싱
        user_key = body.get("userRequest", {}).get("user", {}).get("id", "")
        utterance = body.get("userRequest", {}).get("utterance", "")
        
        # 카카오에서 넘어오는 파라미터 저장
        params = body.get("action", {}).get("params", {}) or {}
        sys_location = params.get("sys_location")  
        food        = params.get("food")          
        location    = params.get("location")       
        

        is_search = ("추천" in utterance) or ("맛집" in utterance) or any([sys_location, food, location])

        if is_search:
            print("[WEBHOOK] params =", {"sys_location": sys_location, "food": food, "location": location})
            geo = await kakao_service.geocode_landmark(location, sys_location)
            print("[WEBHOOK] geo     =", geo)


            if geo:
                lat, lng = geo["lat"], geo["lng"]
                stores = await pinecone_service.search_stores_by_location(lat, lng, radius=5.0, top_k=5)
            else:   
            # 텍스트 기반 검색: 발화 + 파라미터를 하나의 쿼리로 묶어 강화
                terms = [utterance, sys_location, location, food]
                query = " ".join([t for t in terms if t])  # 빈 값은 제외
                stores = await pinecone_service.search_stores_by_text(query, top_k=5)

            if stores:
                # 세션에 검색 결과 저장 → 다음 턴에서 가게 선택 처리
                user_sessions[user_key] = {"mode": "list", "stores": stores}
                return kakao_service.create_list_card_response(stores)

            return kakao_service.create_text_response("죄송합니다. 검색 결과가 없습니다.")

        # 4) 리스트 → 가게 선택 단계
        if user_key in user_sessions and user_sessions[user_key].get("mode") == "list":
            stores = user_sessions[user_key]["stores"]
            selected_store = await openai_service.find_matching_store(utterance, stores)

            if selected_store:
                user_sessions[user_key] = {"mode": "detail", "store": selected_store, "chat_history": []}
                return kakao_service.create_store_detail_response(selected_store)

            return kakao_service.create_text_response("어떤 가게를 선택하시겠어요? 가게 이름을 말씀해주세요.")

        # 5) 상세 모드에서의 자유 질의 → LLM
        if user_key in user_sessions and user_sessions[user_key].get("mode") == "detail":
            store = user_sessions[user_key]["store"]
            chat_history = user_sessions[user_key].get("chat_history", [])
            response = await openai_service.generate_store_response(store, utterance, chat_history)

            chat_history.extend([
                {"role": "user", "content": utterance},
                {"role": "assistant", "content": response},
            ])
            user_sessions[user_key]["chat_history"] = chat_history[-10:]
            return kakao_service.create_text_response(response)

        # 6) 기본 응답
        return kakao_service.create_text_response(
            "안녕하세요! 맛집을 찾아드립니다.\n'근처 맛집 추천해줘' 또는 '한식 맛집 찾아줘'라고 말씀해주세요."
        )

    except Exception as e:
        print(f"Error in webhook: {e}")
        return kakao_service.create_text_response("죄송합니다. 오류가 발생했습니다.")

@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "ok"}
