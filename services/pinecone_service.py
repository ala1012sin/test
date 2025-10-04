from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
import json
from utils.config import config
from services.openai_service import OpenAIService

class PineconeService:
    def __init__(self):
        # Pinecone 초기화 (최신 버전 방식)
        self.pc = Pinecone(api_key=config.PINECONE_API_KEY)
        
        self.index_name = config.PINECONE_INDEX
        self.openai_service = OpenAIService()
        
        # 인덱스가 존재하는지 확인
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            # 인덱스 생성 (Serverless 방식)
            self.pc.create_index(
                name=self.index_name,
                dimension=1536,  # text-embedding-3-small 차원
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region=config.PINECONE_REGION  # 예: 'us-east-1'
                )
            )
        
        self.index = self.pc.Index(self.index_name)
    
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
                store = match['metadata'].copy()
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
    
    async def delete_store(self, survey_id: str) -> bool:
        """상점 삭제"""
        try:
            self.index.delete(ids=[survey_id])
            return True
        except Exception as e:
            print(f"Error deleting store: {e}")
            return False
    
    async def search_stores_by_location(self, latitude: float, longitude: float, 
                                       radius: float = 5.0, top_k: int = 10) -> List[Dict[str, Any]]:
        """위치 기반으로 상점 검색 (주소 텍스트 기반)"""
        location_query = f"위도 {latitude}, 경도 {longitude} 근처"
        return await self.search_stores_by_text(location_query, top_k)
