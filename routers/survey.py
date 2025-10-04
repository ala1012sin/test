from fastapi import APIRouter, HTTPException
from models.schemas import StoreData
from services.pinecone_service import PineconeService

router = APIRouter(prefix="/survey", tags=["survey"])
pinecone_service = PineconeService()

@router.post("/store")
async def register_store(store_data: StoreData):
    """설문조사 데이터를 받아 Pinecone에 저장"""
    try:
        success = await pinecone_service.upsert_store(store_data.dict())
        
        if success:
            return {
                "status": "success",
                "message": "상점 정보가 성공적으로 저장되었습니다.",
                "survey_id": store_data.surveyId
            }
        else:
            raise HTTPException(status_code=500, detail="상점 정보 저장 실패")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/store/{survey_id}")
async def get_store(survey_id: str):
    """상점 정보 조회"""
    store = await pinecone_service.get_store_by_id(survey_id)
    
    if store:
        return {"status": "success", "data": store}
    else:
        raise HTTPException(status_code=404, detail="상점을 찾을 수 없습니다.")
