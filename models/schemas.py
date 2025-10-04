from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import time

class Service(BaseModel):
    menu: str
    price: float

class StoreData(BaseModel):
    surveyId: str
    name: str
    industry: str
    address: str
    phone: str
    openingHourStart: str
    openingHourEnd: str
    holidays: List[str]
    services: List[Service]
    strengths: Optional[str] = ""
    parkingInfo: Optional[str] = ""
    snsUrl: Optional[str] = ""

class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    radius: Optional[float] = 5.0  # km


# 수정 해야 함
class KakaoUserRequest(BaseModel):
    user_key: str
    utterance: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class KakaoResponse(BaseModel):
    version: str = "2.0"
    template: dict

class ChatRequest(BaseModel):
    store_id: str
    user_message: str
    chat_history: Optional[List[dict]] = []
