# pinecone_service.py

from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
import json
from utils.config import config
from services.openai_service import OpenAIService
import math

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
                    region=config.PINECONE_REGION
                )
            )
        
        self.index = self.pc.Index(self.index_name)

        # 인덱스 정보 출력
        index_info = self.index.describe_index_stats()
        print(f"\n{'='*80}")
        print(f"Pinecone Index '{self.index_name}' initialized")
        print(f"{'='*80}")
        print(f"Total vectors: {index_info['total_vector_count']}")
        print(f"Dimension: {index_info.get('dimension', 1536)}")
        print(f"{'='*80}\n")

        self.debug_print_all_vectors()

    # ==================== 메타데이터 파싱 유틸리티 ====================
    
    def parse_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pinecone 메타데이터를 파싱하여 사용 가능한 형태로 변환
        """
        parsed = {}
        
        # 기본 필드 복사
        for key, value in metadata.items():
            if key == 'services':
                # services 필드를 JSON으로 파싱
                try:
                    if isinstance(value, str):
                        # 작은따옴표를 큰따옴표로 변경
                        services_str = value.replace("'", '"')
                        parsed['services'] = json.loads(services_str)
                    else:
                        parsed['services'] = value
                except Exception as e:
                    print(f"Error parsing services: {e}")
                    parsed['services'] = []
            elif key == 'holidays':
                # holidays가 빈 문자열이면 빈 리스트로
                parsed['holidays'] = [] if value == "" else value.split(',') if isinstance(value, str) else value
            else:
                parsed[key] = value
        
        return parsed
    
    def print_store_data(self, store_data: Dict[str, Any], title: str = "Store Data"):
        """
        상점 데이터를 콘솔에 예쁘게 출력
        """
        print(f"\n{'-'*80}")
        print(f"{title}")
        print(f"{'-'*80}")
        
        # 기본 정보
        print(f"ID           : {store_data.get('surveyId', 'N/A')}")
        print(f"Name         : {store_data.get('name', 'N/A')}")
        print(f"Industry     : {store_data.get('industry', 'N/A')}")
        print(f"Address      : {store_data.get('address', 'N/A')}")
        print(f"Phone        : {store_data.get('phone', 'N/A')}")
        print(f"Opening Hours: {store_data.get('openingHourStart', 'N/A')} - {store_data.get('openingHourEnd', 'N/A')}")
        print(f"Holidays     : {store_data.get('holidays', 'N/A')}")
        print(f"Parking      : {store_data.get('parkingInfo', 'N/A')}")
        print(f"Strengths    : {store_data.get('strengths', 'N/A')}")
        print(f"SNS URL      : {store_data.get('snsUrl', 'N/A')}")
        
        # 서비스/메뉴 정보
        services = store_data.get('services', [])
        if services:
            print(f"\nServices/Menu:")
            for i, service in enumerate(services, 1):
                menu = service.get('menu', 'N/A')
                price = service.get('price', 'N/A')
                print(f"  {i}. {menu}: {price}원")
        
        print(f"{'-'*80}\n")

    # ==================== 검색 ====================
    
    async def search_stores_by_text(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """텍스트 검색으로 상점 찾기"""
        try:
            print(f"\n{'='*80}")
            print(f"Searching stores")
            print(f"{'='*80}")
            print(f"Query: {query}")
            print(f"Top K: {top_k}\n")
            
            # 쿼리 임베딩
            print(f"Creating query embedding...")
            query_embedding = await self.openai_service.create_embedding(query)
            print(f"Query embedding created\n")
            
            # 검색
            print(f"Searching in Pinecone...")
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            print(f"Found {len(results['matches'])} results\n")
            
            stores = []
            for i, match in enumerate(results['matches'], 1):
                metadata = match['metadata']
                
                # 메타데이터 파싱
                parsed_store = self.parse_metadata(metadata)
                
                # 콘솔에 출력
                print(f"Result #{i} (Score: {match['score']:.4f})")
                self.print_store_data(parsed_store)
                
                store = {
                    'surveyId': parsed_store.get('surveyId', parsed_store.get('survey_id', '')),
                    'name': parsed_store.get('name', ''),
                    'industry': parsed_store.get('industry', ''),
                    'address': parsed_store.get('address', ''),
                    'phone': parsed_store.get('phone', ''),
                    'openingHourStart': parsed_store.get('openingHourStart', ''),
                    'openingHourEnd': parsed_store.get('openingHourEnd', ''),
                    'holidays': parsed_store.get('holidays', []),
                    'services': parsed_store.get('services', []),
                    'strengths': parsed_store.get('strengths', ''),
                    'parkingInfo': parsed_store.get('parkingInfo', ''),
                    'snsUrl': parsed_store.get('snsUrl', ''),
                    'score': match['score']
                }
                
                stores.append(store)
            
            print(f"{'='*80}\n")
            return stores
            
        except Exception as e:
            print(f"\nError searching stores: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_store_by_id(self, survey_id: str) -> Optional[Dict[str, Any]]:
        """ID로 상점 정보 가져오기"""
        try:
            print(f"\n{'='*80}")
            print(f"Fetching store by ID")
            print(f"{'='*80}")
            print(f"Survey ID: {survey_id}\n")
            
            # Pinecone에서 fetch
            result = self.index.fetch(ids=[survey_id])
            
            if survey_id not in result['vectors']:
                print(f"Store not found: {survey_id}\n")
                return None
            
            metadata = result['vectors'][survey_id]['metadata']
            
            # 메타데이터 파싱
            parsed_store = self.parse_metadata(metadata)
            
            # 콘솔에 출력
            self.print_store_data(parsed_store, f"Store Details: {parsed_store.get('name', 'Unknown')}")
            
            store = {
                'surveyId': parsed_store.get('surveyId', parsed_store.get('survey_id', '')),
                'name': parsed_store.get('name', ''),
                'industry': parsed_store.get('industry', ''),
                'address': parsed_store.get('address', ''),
                'phone': parsed_store.get('phone', ''),
                'openingHourStart': parsed_store.get('openingHourStart', ''),
                'openingHourEnd': parsed_store.get('openingHourEnd', ''),
                'holidays': parsed_store.get('holidays', []),
                'services': parsed_store.get('services', []),
                'strengths': parsed_store.get('strengths', ''),
                'parkingInfo': parsed_store.get('parkingInfo', ''),
                'snsUrl': parsed_store.get('snsUrl', '')
            }

            print(f"{'='*80}\n")
            return store
            
        except Exception as e:
            print(f"\nError fetching store: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def search_stores_by_location(self, latitude: float, longitude: float, radius_km: float = 5.0, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        위도/경도 기반으로 주변 상점 검색
        
        Args:
            latitude: 위도
            longitude: 경도
            radius_km: 검색 반경 (킬로미터, 기본값 5km)
            top_k: 최대 결과 개수
        
        Returns:
            거리순으로 정렬된 상점 리스트
        """
        try:
            print(f"\n{'='*80}")
            print(f"Searching stores by location")
            print(f"{'='*80}")
            print(f"Latitude: {latitude}")
            print(f"Longitude: {longitude}")
            print(f"Radius: {radius_km}km")
            print(f"Top K: {top_k}\n")
            
            # Pinecone 메타데이터 필터로 검색
            # 먼저 더 많은 결과를 가져온 후 거리로 필터링
            results = self.index.query(
                vector=[0.0] * 1536,  # 더미 벡터 (메타데이터만 사용)
                top_k=100,  # 충분히 많이 가져오기
                include_metadata=True
            )
            
            stores_with_distance = []
            
            for match in results['matches']:
                metadata = match['metadata']
                
                # 위도/경도가 있는지 확인
                if 'latitude' not in metadata or 'longitude' not in metadata:
                    continue
                
                store_lat = float(metadata['latitude'])
                store_lon = float(metadata['longitude'])
                
                # 거리 계산
                distance = self.calculate_distance(latitude, longitude, store_lat, store_lon)
                
                # 반경 내에 있는지 확인
                if distance <= radius_km:
                    parsed_store = self.parse_metadata(metadata)
                    
                    store = {
                        'surveyId': parsed_store.get('surveyId', parsed_store.get('survey_id', '')),
                        'name': parsed_store.get('name', ''),
                        'industry': parsed_store.get('industry', ''),
                        'address': parsed_store.get('address', ''),
                        'phone': parsed_store.get('phone', ''),
                        'openingHourStart': parsed_store.get('openingHourStart', ''),
                        'openingHourEnd': parsed_store.get('openingHourEnd', ''),
                        'holidays': parsed_store.get('holidays', []),
                        'services': parsed_store.get('services', []),
                        'strengths': parsed_store.get('strengths', ''),
                        'parkingInfo': parsed_store.get('parkingInfo', ''),
                        'snsUrl': parsed_store.get('snsUrl', ''),
                        'latitude': store_lat,
                        'longitude': store_lon,
                        'distance': round(distance, 2)  # km 단위, 소수점 2자리
                    }
                    
                    stores_with_distance.append(store)
            
            # 거리순으로 정렬
            stores_with_distance.sort(key=lambda x: x['distance'])
            
            # top_k개만 반환
            result_stores = stores_with_distance[:top_k]
            
            print(f"Found {len(result_stores)} stores within {radius_km}km\n")
            
            # 결과 출력
            for i, store in enumerate(result_stores, 1):
                print(f"Result #{i} (Distance: {store['distance']}km)")
                self.print_store_data(store)
            
            print(f"{'='*80}\n")
            return result_stores
            
        except Exception as e:
            print(f"\nError searching stores by location: {e}")
            import traceback
            traceback.print_exc()
            return []


    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        두 좌표 간의 거리를 계산 (Haversine 공식)
        반환값: 킬로미터 단위 거리
        """
        R = 6371  # 지구 반지름 (km)
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2) * math.sin(delta_lat/2) + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(delta_lon/2) * math.sin(delta_lon/2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance = R * c
        return distance


    def debug_print_all_vectors(self, limit: int = 3):
        """
        디버깅용: Pinecone에 저장된 벡터 샘플 출력
        """
        try:
            print(f"\n{'='*80}")
            print(f"Debug: Sample Vectors in Pinecone")
            print(f"{'='*80}\n")
            
            # 더미 쿼리로 샘플 가져오기
            results = self.index.query(
                vector=[0.0] * 1536,
                top_k=limit,
                include_metadata=True
            )
            
            for i, match in enumerate(results['matches'], 1):
                metadata = match['metadata']
                parsed_store = self.parse_metadata(metadata)
                
                print(f"Sample #{i}")
                self.print_store_data(parsed_store)
            
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"Error in debug_print_all_vectors: {e}\n")
