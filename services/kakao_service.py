import os
from typing import Optional, List, Dict, Any
import httpx

class KakaoService:
    @staticmethod
    def create_text_response(text: str) -> Dict[str, Any]:
        """간단한 텍스트 응답"""
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": text
                        }
                    }
                ]
            }
        }
    
    @staticmethod
    def create_list_card_response(stores: List[Dict[str, Any]]) -> Dict[str, Any]:
        items = []
        for s in stores[:5]:
            services = s.get('services') or []
            menu_text = ", ".join([sv.get('menu', '') for sv in services[:3] if sv.get('menu')])
            items.append({
                "title": (s.get('name') or "")[:30],
                "description": f"{s.get('industry', '')} | {s.get('address', '')}\n메뉴: {menu_text}"[:100],
                "thumbnail": {"imageUrl": s.get('image_url', '')},
                "buttons": [{
                "label": "상세보기",
                "action": "block",
                "blockId": "68e34208edb87047afdef653",
                "extra": {
                    "store_id": s.get('id'),
                    "store_name": s.get('name', "")
                }
            }]
        })

        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "carousel": {
                            "type": "basicCard",
                            "items": items
                        }
                    }
                ]
            }
        }
    
    @staticmethod
    def create_store_detail_response(store: Dict[str, Any]) -> Dict[str, Any]:
        """상점 상세 정보 응답"""
        services = store.get('services', [])
        menu_text = "\n".join([f"• {s['menu']}: {s['price']:,}원" for s in services])
        
        description = f"""
📍 주소: {store['address']}
📞 전화: {store['phone']}
⏰ 영업시간: {store['opening_hour_start']} ~ {store['opening_hour_end']}
🚫 휴무일: {', '.join(store['holidays'])}

📋 메뉴:
{menu_text}
"""
        
        if store.get('strengths'):
            description += f"\n✨ 강점: {store['strengths']}"
        
        if store.get('parking_info'):
            description += f"\n🅿️ 주차: {store['parking_info']}"
        
        buttons = []
        if store.get('phone'):
            buttons.append({
                "label": "전화하기",
                "action": "phone",
                "phoneNumber": store['phone']
            })
        
        if store.get('sns_url'):
            buttons.append({
                "label": "SNS 보기",
                "action": "webLink",
                "webLinkUrl": store['sns_url']
            })
        
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "basicCard": {
                            "title": store['name'],
                            "description": description.strip(),
                            "buttons": buttons
                        }
                    }
                ]
            }
        }

    @staticmethod
    async def geocode_landmark(location_text: Optional[str], fallback_text: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        우선순위: location_text -> fallback_text(sys_location)
        카카오 로컬 API로 좌표(lat, lng) 조회. 성공 시 {"lat": float, "lng": float, "name": str} 반환.
        """
        query = (location_text or fallback_text or "").strip()
        if not query:
            return None

        api_key = os.getenv("KAKAO_REST_API_KEY", "")
        if not api_key:
            # 키 없으면 좌표 변환 불가
            return None

        headers = {"Authorization": f"KakaoAK {api_key}"}
        base = "https://dapi.kakao.com"

        # 1) 키워드 검색
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{base}/v2/local/search/keyword.json",
                                     params={"query": query, "size": 1},
                                     headers=headers)
                if r.status_code == 200:
                    docs = r.json().get("documents", [])
                    if docs:
                        y = float(docs[0]["y"])  # lat
                        x = float(docs[0]["x"])  # lng
                        name = docs[0].get("place_name") or query
                        return {"lat": y, "lng": x, "name": name}

                # 2) 주소 검색 (키워드 실패 시)
                r2 = await client.get(f"{base}/v2/local/search/address.json",
                                      params={"query": query},
                                      headers=headers)
                if r2.status_code == 200:
                    docs = r2.json().get("documents", [])
                    if docs:
                        d = docs[0]
                        y = float(d["y"])
                        x = float(d["x"])
                        name = d.get("address_name") or query
                        return {"lat": y, "lng": x, "name": name}
        except Exception:
            # 타임아웃/네트워크 예외는 None 반환
            return None

        return None