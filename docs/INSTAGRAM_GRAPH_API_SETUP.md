# Instagram Graph API Setup Guide

Instagram Graph API를 통한 합법적인 비즈니스 계정 콘텐츠 접근 설정 가이드입니다.

## 📋 사전 요구사항

1. **Instagram 비즈니스 또는 크리에이터 계정**
   - 개인 계정을 비즈니스 계정으로 전환 필요
   - 설정 > 계정 > 프로페셔널 계정으로 전환

2. **Facebook 페이지**
   - Instagram 비즈니스 계정을 Facebook 페이지에 연결 필요
   - https://www.facebook.com/pages/create

3. **Meta 개발자 계정**
   - https://developers.facebook.com/ 에서 무료 등록

## 🚀 설정 단계

### 1단계: Facebook App 생성

1. [Meta for Developers](https://developers.facebook.com/apps/) 접속
2. "앱 만들기" 클릭
3. 앱 유형 선택: **"비즈니스"** 또는 **"소비자"**
4. 앱 정보 입력:
   - 앱 이름: `SNS Download Service` (원하는 이름)
   - 앱 연락처 이메일
   - 비즈니스 계정 선택 (선택사항)

### 2단계: Instagram Graph API 추가

1. 생성된 앱 대시보드에서 "제품 추가" 클릭
2. **"Instagram"** 제품 선택 후 "설정" 클릭
3. Instagram Graph API가 앱에 추가됨

### 3단계: 앱 설정

**앱 대시보드 > 설정 > 기본 설정**에서:

```
앱 ID: 123456789012345
앱 시크릿: abcdef1234567890abcdef1234567890
```

이 정보를 `.env` 파일에 저장:

```bash
FACEBOOK_APP_ID=123456789012345
FACEBOOK_APP_SECRET=abcdef1234567890abcdef1234567890
```

### 4단계: Access Token 생성

#### 개발/테스트용 (단기 토큰)

1. [Graph API Explorer](https://developers.facebook.com/tools/explorer/) 접속
2. 상단에서 생성한 앱 선택
3. "권한" 탭에서 다음 권한 추가:
   - `instagram_basic`
   - `pages_read_engagement`
   - `pages_show_list`
4. "Generate Access Token" 클릭
5. Instagram 계정으로 로그인 및 권한 승인

생성된 토큰을 `.env`에 저장:

```bash
INSTAGRAM_GRAPH_API_TOKEN=your_short_lived_token_here
```

⚠️ **주의**: 이 토큰은 1시간 후 만료됩니다.

#### 프로덕션용 (장기 토큰)

장기 토큰으로 교환:

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id={FACEBOOK_APP_ID}&client_secret={FACEBOOK_APP_SECRET}&fb_exchange_token={SHORT_LIVED_TOKEN}"
```

응답에서 받은 장기 토큰을 `.env`에 저장:

```bash
INSTAGRAM_GRAPH_API_TOKEN=your_long_lived_token_here
```

장기 토큰은 **60일** 유효합니다.

### 5단계: Instagram 비즈니스 계정 ID 확인

자신의 Instagram 비즈니스 계정 ID 확인:

```bash
curl -X GET "https://graph.facebook.com/v18.0/me/accounts?access_token={INSTAGRAM_GRAPH_API_TOKEN}"
```

응답에서 `instagram_business_account` ID를 확인합니다.

## 🔧 API 사용 예시

### 자신의 미디어 목록 조회

```bash
curl -X GET "https://graph.facebook.com/v18.0/me/media?fields=id,media_type,media_url,thumbnail_url,permalink,caption,timestamp&access_token={TOKEN}"
```

### 특정 미디어 정보 조회

```bash
curl -X GET "https://graph.facebook.com/v18.0/{MEDIA_ID}?fields=id,media_type,media_url,thumbnail_url,permalink,caption,timestamp,username&access_token={TOKEN}"
```

## 🎯 API 사용 예시 (Python)

```python
from app.platforms.instagram_graph import InstagramGraphPlatform

# 초기화
platform = InstagramGraphPlatform(access_token="your_token_here")

# 자신의 미디어 목록 조회
media_list = platform.list_user_media(limit=25)

for item in media_list['data']:
    print(f"Media ID: {item['id']}")
    print(f"Type: {item['media_type']}")
    print(f"URL: {item['permalink']}")
    print("---")
```

## ⚠️ 제약 사항

### 1. 접근 범위
- **자신의 비즈니스 계정만** 접근 가능
- 다른 사용자의 콘텐츠는 접근 불가
- Business Discovery API로 제한적 정보 조회 가능

### 2. Rate Limits
- **기본**: 200 calls/hour per user
- **앱 수준**: 앱 전체 사용자에 대한 통합 제한
- 429 에러 발생 시 백오프 필요

### 3. 미디어 유형
- ✅ **IMAGE**: 사진 다운로드 가능
- ✅ **VIDEO**: 비디오 다운로드 가능
- ✅ **CAROUSEL_ALBUM**: 캐러셀 다운로드 가능 (children 필드로 접근)

### 4. 앱 검수
개발 모드에서는:
- 앱 관리자, 개발자, 테스터만 사용 가능
- 최대 25명까지 테스터 추가 가능

프로덕션 배포 시:
- Meta App Review 필요
- 승인까지 수일~수주 소요

## 🔐 보안 권장사항

1. **토큰 보안**
   ```bash
   # .env 파일은 절대 git에 커밋하지 않기
   echo ".env" >> .gitignore
   ```

2. **토큰 갱신**
   - 장기 토큰도 60일마다 갱신 필요
   - 자동 갱신 로직 구현 권장

3. **권한 최소화**
   - 필요한 권한만 요청
   - `instagram_basic`만으로도 기본 미디어 접근 가능

## 📚 참고 자료

- [Instagram Graph API 공식 문서](https://developers.facebook.com/docs/instagram-api)
- [Access Token 디버거](https://developers.facebook.com/tools/debug/accesstoken/)
- [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
- [권한 참조](https://developers.facebook.com/docs/permissions/reference)

## 🤝 지원

문제가 발생하면:
1. [Meta Developer Community](https://developers.facebook.com/community/)
2. [Stack Overflow - instagram-graph-api 태그](https://stackoverflow.com/questions/tagged/instagram-graph-api)
