from typing import List, Dict, Any

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
        """상점 리스트 카드 응답"""
        items = []
        for store in stores[:5]:  # 최대 5개
            services = store.get('services', [])
            menu_text = ", ".join([s['menu'] for s in services[:3]])
            
            items.append({
                "title": store['name'],
                "description": f"{store['industry']} | {store['address']}\n메뉴: {menu_text}",
                "imageUrl": "",  # 이미지가 있다면 추가
                "link": {
                    "web": store.get('sns_url', '')
                }
            })
        
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "listCard": {
                            "header": {
                                "title": "추천 맛집 리스트"
                            },
                            "items": items,
                            "buttons": [
                                {
                                    "label": "더보기",
                                    "action": "block",
                                    "blockId": ""  # 블록 ID 설정 필요
                                }
                            ]
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
