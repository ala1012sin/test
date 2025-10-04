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
        
        # 위치 정보 (있는 경우)
        params = body.get("action", {}).get("params", {})
        latitude = params.get("latitude")
        longitude = params.get("longitude")
        
        # 사용자 의도 파악
        if "추천" in utterance or "맛집" in utterance:
            # 음식점 추천 시나리오
            if latitude and longitude:
                # 위치 기반 검색
                stores = await pinecone_service.search_stores_by_location(
                    float(latitude), float(longitude), radius=5.0, top_k=5
                )
            else:
                # 텍스트 기반 검색
                stores = await pinecone_service.search_stores_by_text(utterance, top_k=5)
            
            if stores:
                # 세션에 검색 결과 저장
                user_sessions[user_key] = {
                    "mode": "list",
                    "stores": stores
                }
                return kakao_service.create_list_card_response(stores)
            else:
                return kakao_service.create_text_response("죄송합니다. 검색 결과가 없습니다.")
        
        elif user_key in user_sessions and user_sessions[user_key]["mode"] == "list":
            # 상점 선택 시나리오
            stores = user_sessions[user_key]["stores"]
            selected_store = await openai_service.find_matching_store(utterance, stores)
            
            if selected_store:
                # 상점 상세 모드로 전환
                user_sessions[user_key] = {
                    "mode": "detail",
                    "store": selected_store
                }
                return kakao_service.create_store_detail_response(selected_store)
            else:
                return kakao_service.create_text_response(
                    "어떤 가게를 선택하시겠어요? 가게 이름을 말씀해주세요."
                )
        
        elif user_key in user_sessions and user_sessions[user_key]["mode"] == "detail":
            # 상점 상세 정보 대화 시나리오
            store = user_sessions[user_key]["store"]
            chat_history = user_sessions[user_key].get("chat_history", [])
            
            # GPT로 답변 생성
            response = await openai_service.generate_store_response(
                store, utterance, chat_history
            )
            
            # 대화 히스토리 업데이트
            chat_history.append({"role": "user", "content": utterance})
            chat_history.append({"role": "assistant", "content": response})
            user_sessions[user_key]["chat_history"] = chat_history[-10:]  # 최근 10개만 유지
            
            return kakao_service.create_text_response(response)
        
        else:
            # 기본 응답
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
