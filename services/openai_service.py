from openai import AsyncOpenAI
from typing import List, Dict, Any
from utils.config import config


def _pick(store: Dict[str, Any], keys: List[str], default: str = "") -> Any:
    """여러 후보 키 중 먼저 존재하는 값을 가져온다."""
    for k in keys:
        v = store.get(k)
        if v is not None:
            return v
    return default

def _fmt_price(p) -> str:
    try:
        # 숫자는 천단위 콤마
        return f"{int(p):,}"
    except Exception:
        # 문자열 등은 그대로
        return str(p)
    

class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_API_MODEL
        self.embedding_model = config.PINECONE_EMBEDDING_MODEL
    
    async def create_embedding(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환"""
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    async def chat_completion(self, messages: List[Dict[str, str]], 
                             temperature: float = 0.7) -> str:
        """GPT 채팅 완성"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content
    
    # 사용자 질문과 매칭되는 상점 찾기(상점 스위칭)
    async def find_matching_store(self, user_query: str, 
                                  store_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """사용자 질문과 매칭되는 상점 찾기"""
        stores_text = "\n".join([
            f"{i+1}. {store['name']} - {store['address']} ({store['industry']})"
            for i, store in enumerate(store_list)
        ])
        
        prompt = f"""
다음은 사용자가 찾고 있는 상점 목록입니다:
{stores_text}
\n
사용자 질문: "{user_query}"

위 목록에서 사용자가 찾는 상점의 번호만 숫자로 답변해주세요. 
만약 명확하지 않다면 0을 반환하세요.
"""
        
        messages = [
            {"role": "system", "content": "당신은 사용자의 질문을 분석하여 적절한 상점을 찾아주는 어시스턴트입니다."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.chat_completion(messages, temperature=0.3)
        
        try:
            index = int(response.strip()) - 1
            if 0 <= index < len(store_list):
                return store_list[index]
        except:
            pass
        
        return None

    # 상점 정보를 바탕으로 사용자 질문에 답변 생성
    # 결정된 상점의 챗봇 상담원 페르소나 데이터를 바탕으로 AI가 답변 생성하도록 수정
    async def generate_store_response(
        self,
        store_info: Dict[str, Any],
        user_message: str,
        chat_history: List[Dict[str, str]] = [],
    ) -> str:
        """상점 정보를 바탕으로 사용자 질문에 답변 생성 (키 안전/보정 버전)"""

        # ---- 키 보정/안전 조회 ----
        name        = _pick(store_info, ["name"], "가게")
        persona     = _pick(store_info, ["persona"], f"상냥하고 도움이 되는 {name} 매장 직원")
        industry    = _pick(store_info, ["industry"], "")
        address     = _pick(store_info, ["address"], "")
        phone       = _pick(store_info, ["phone"], "")
        open_start  = _pick(store_info, ["opening_hour_start", "openingHourStart"], "")
        open_end    = _pick(store_info, ["opening_hour_end", "openingHourEnd"], "")
        strengths   = _pick(store_info, ["strengths"], "정보 없음")
        parking     = _pick(store_info, ["parking_info", "parkingInfo"], "정보 없음")
        sns         = _pick(store_info, ["sns_url", "snsUrl"], "정보 없음")

        # 휴무일은 리스트/문자열 모두 처리
        holidays_raw = _pick(store_info, ["holidays"], [])
        if isinstance(holidays_raw, list):
            holidays = ", ".join([str(h) for h in holidays_raw if str(h).strip() and str(h) != "[]"]) or "없음"
        elif isinstance(holidays_raw, str):
            holidays = holidays_raw if holidays_raw.strip() else "없음"
        else:
            holidays = "없음"

        # 메뉴/서비스 보정
        services = store_info.get("services") or []
        lines = []
        for s in services:
            menu  = _pick(s, ["menu", "name"], "")
            price = _pick(s, ["price", "amount"], "")
            if menu:
                price_txt = f": {_fmt_price(price)}원" if price not in ("", None) else ""
                lines.append(f"- {menu}{price_txt}")
        services_text = "\n".join(lines) if lines else "- (등록된 메뉴 정보가 없습니다)"

        # ---- 프롬프트 구성 (기존 톤 최대한 유지) ----
        system_prompt = f"""당신은 '{name}'의 친절한 챗봇 상담원입니다.
{persona}에 맞게 답변해주어야 합니다.

[상점 정보]
- 상점명: {name}
- 업종: {industry}
- 주소: {address}
- 전화번호: {phone}
- 영업시간: {open_start} ~ {open_end}
- 휴무일: {holidays}
- 메뉴:
{services_text}
- 강점: {strengths}
- 주차정보: {parking}
- SNS: {sns}

위 정보를 바탕으로 고객의 질문에 친절하고 정확하게 답변해주세요.
정보가 없는 경우 솔직하게 알려주세요.
"""

        messages = [{"role": "system", "content": system_prompt}]
        # 이전 대화 히스토리(있다면) 이어붙이기
        if chat_history:
            messages.extend(chat_history)
        # 이번 사용자 질문
        messages.append({"role": "user", "content": user_message or "안녕하세요. 무엇을 도와드릴까요?"})

        return await self.chat_completion(messages)