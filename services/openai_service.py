from openai import AsyncOpenAI
from typing import List, Dict, Any
from utils.config import config

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
    async def generate_store_response(self, store_info: Dict[str, Any], 
                                     user_message: str,
                                     chat_history: List[Dict[str, str]] = []) -> str:
        """상점 정보를 바탕으로 사용자 질문에 답변 생성"""
        
        services_text = "\n".join([f"- {s['menu']}: {s['price']}원" for s in store_info['services']])
        
        system_prompt = f"""
당신은 '{store_info['name']}'의 친절한 챗봇 상담원입니다.
{store_info['persona']}에 맞게 답변해주어야 합니다.

[상점 정보]
- 상점명: {store_info['name']}
- 업종: {store_info['industry']}
- 주소: {store_info['address']}
- 전화번호: {store_info['phone']}
- 영업시간: {store_info['openingHourStart']} ~ {store_info['openingHourEnd']}
- 휴무일: {', '.join(store_info['holidays'])}
- 메뉴:
{services_text}
- 강점: {store_info.get('strengths', '없음')}
- 주차정보: {store_info.get('parkingInfo', '없음')}
- SNS: {store_info.get('snsUrl', '없음')}

위 정보를 바탕으로 고객의 질문에 친절하고 정확하게 답변해주세요.
정보가 없는 경우 솔직하게 알려주세요.
"""
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(chat_history)
        messages.append({"role": "user", "content": user_message})
        
        return await self.chat_completion(messages)
