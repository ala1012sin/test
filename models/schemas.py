from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import time

# 음식점 메뉴 항목
class Service(BaseModel):
    menu: str
    price: str  # 가격을 문자열로 변경 (12,500 형식 지원)

# 음식점 데이터 모델
class StoreData(BaseModel):
    surveyId: str
    name: str
    industry: str
    address: str
    phone: str
    openingHourStart: str
    openingHourEnd: str
    holidays: List[str] = []  # 기본값 빈 리스트
    services: List[Service] = []  # 기본값 빈 리스트
    strengths: Optional[str] = ""
    parkingInfo: Optional[str] = ""
    snsUrl: Optional[str] = ""

# 검색 결과 모델
class StoreSearchResult(StoreData):
    score: float  # 검색 점수 추가

# 사용자 위치 요청 모델
class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    radius: Optional[float] = 5.0  # km


# 수정 해야 함
# 카카오톡 요청 및 응답 모델
class KakaoParams(BaseModel):
    sys_location: Optional[str] = None
    food: Optional[str] = None        
    location: Optional[str] = None     

class KakaoResponse(BaseModel):
    version: str = "2.0"
    template: dict


class ChatRequest(BaseModel):
    store_id: str
    user_message: str
    chat_history: Optional[List[dict]] = []
