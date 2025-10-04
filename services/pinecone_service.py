from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any
import json
from utils.config import config
from services.openai_service import OpenAIService

class PineconeService:
    def __init__(self):
        self.pc = Pinecone(api_key=config.PINECONE_API_KEY)
        self.index_name = config.PINECONE_INDEX
        self.openai_service = OpenAIService()
        
        # 인덱스 연결
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name,
                dimension=1536,  # text-embedding-3-small 차원
                metric='cosine',
                spec=ServerlessSpec(
                    cloud=config.PINECONE_CLOUD,
                    region=config.PINECONE_REGION
                )
            )
        
        self.index = self.pc.Index(self.index_name)
    
    def create_store_text(self, store_data: Dict[str, Any]) -> str:
        """상점 데이터를 텍스트로 변환"""
        services_text = ", ".join([f"{s['menu']} {s['price']}원" for s in store_data['services']])
        holidays_text = ", ".join(store_data['holidays'])
        
        text = f"""
        상점명: {store_data['name']}
        업종: {store_data['industry']}
        주소: {store_data['address']}
        전화번호: {store_data['phone']}
        영업시간: {store_data['openingHourStart']} ~ {store_data['openingHourEnd']}
        휴무일: {holidays_text}
        메뉴: {services_text}
        강점: {store_data.get('strengths', '')}
        주차정보: {store_data.get('parkingInfo', '')}
        SNS: {store_data.get('snsUrl', '')}
        """
        return text.strip()
    
    async def upsert_store(self, store_data: Dict[str, Any]) -> bool:
        """상점 데이터를 Pinecone에 저장"""
        try:
            # 텍스트 생성
            store_text = self.create_store_text(store_data)
            
            # 임베딩 생성
            embedding = await self.openai_service.create_embedding(store_text)
            
            # 메타데이터 준비
            metadata = {
                "survey_id": store_data['surveyId'],
                "name": store_data['name'],
                "industry": store_data['industry'],
                "address": store_data['address'],
                "phone": store_data['phone'],
                "opening_hour_start": store_data['openingHourStart'],
                "opening_hour_end": store_data['openingHourEnd'],
                "holidays": json.dumps(store_data['holidays'], ensure_ascii=False),
                "services": json.dumps(store_data['services'], ensure_ascii=False),
                "strengths": store_data.get('strengths', ''),
                "parking_info": store_data.get('parkingInfo', ''),
                "sns_url": store_data.get('snsUrl', ''),
                "text": store_text
            }
            
            # Pinecone에 업서트
            self.index.upsert(
                vectors=[
                    {
                        "id": store_data['surveyId'],
                        "values": embedding,
                        "metadata": metadata
                    }
                ]
            )
            
            return True
        except Exception as e:
            print(f"Error upserting store: {e}")
            return False
    
    async def search_stores_by_text(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """텍스트 검색으로 상점 찾기"""
        try:
            # 쿼리 임베딩
            query_embedding = await self.openai_service.create_embedding(query)
            
            # 검색
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            stores = []
            for match in results['matches']:
                store = match['metadata']
                store['score'] = match['score']
                store['services'] = json.loads(store['services'])
                store['holidays'] = json.loads(store['holidays'])
                stores.append(store)
            
            return stores
        except Exception as e:
            print(f"Error searching stores: {e}")
            return []
    
    async def get_store_by_id(self, survey_id: str) -> Optional[Dict[str, Any]]:
        """ID로 상점 정보 가져오기"""
        try:
            result = self.index.fetch(ids=[survey_id])
            if survey_id in result['vectors']:
                metadata = result['vectors'][survey_id]['metadata']
                metadata['services'] = json.loads(metadata['services'])
                metadata['holidays'] = json.loads(metadata['holidays'])
                return metadata
            return None
        except Exception as e:
            print(f"Error fetching store: {e}")
            return None
    
    async def search_stores_by_location(self, latitude: float, longitude: float, 
                                       radius: float = 5.0, top_k: int = 10) -> List[Dict[str, Any]]:
        """위치 기반으로 상점 검색 (주소 텍스트 기반)"""
        # 위치 기반 검색 쿼리 생성
        location_query = f"위도 {latitude}, 경도 {longitude} 근처"
        return await self.search_stores_by_text(location_query, top_k)
