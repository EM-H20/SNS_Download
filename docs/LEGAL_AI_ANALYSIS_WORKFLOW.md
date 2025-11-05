# Legal AI Analysis Workflow Documentation

합법적인 AI 분석 워크플로우 - Fair Use 준수 아키텍처

## 🎯 개요 (Overview)

이 시스템은 SNS 동영상을 합법적으로 AI 분석하는 워크플로우를 제공합니다.
저작권 침해 없이 Fair Use (공정 이용) 원칙에 따라 변형적 사용(transformative use)을 구현합니다.

**핵심 원칙**:
1. **동영상**: 임시 다운로드 → AI 분석 → 텍스트 추출 → 즉시 삭제
2. **사진/썸네일**: 서버 다운로드 없이 웹뷰로 직접 표시
3. **영구 저장**: 분석 결과 텍스트만 저장, 원본 미디어는 삭제

## 📐 아키텍처 (Architecture)

### 시스템 구성요소

```
┌─────────────────────────────────────────────────────────────┐
│                    SNS URL 입력                              │
│         (Instagram, YouTube, TikTok, etc.)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
            ┌────────▼────────┐
            │  미디어 타입 판단  │
            └────────┬────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   ┌────▼─────┐            ┌─────▼──────┐
   │  VIDEO   │            │   PHOTO    │
   │  경로     │            │   경로      │
   └────┬─────┘            └─────┬──────┘
        │                         │
┌───────▼────────┐         ┌─────▼──────────┐
│  임시 다운로드   │         │ 웹뷰 embed URL │
│  /downloads/temp│         │  직접 반환      │
└───────┬────────┘         └────────────────┘
        │
┌───────▼────────┐
│   AI 분석       │
│  (Mock/실제)   │
└───────┬────────┘
        │
┌───────▼────────┐
│  텍스트 추출    │
│  - 요약         │
│  - 설명         │
│  - 키워드       │
└───────┬────────┘
        │
┌───────▼────────┐
│  원본 동영상    │
│   즉시 삭제     │
└───────┬────────┘
        │
┌───────▼────────┐
│ 분석 결과 저장  │
│  (텍스트만)    │
└────────────────┘
```

## 🔧 구현된 컴포넌트

### 1. 임시 저장소 관리 (`app/temp_storage.py`)

**목적**: 동영상 임시 저장 및 자동 삭제

**주요 기능**:
- 임시 디렉토리 생성 (`downloads/temp/`)
- Context manager를 통한 안전한 파일 접근
- 자동 삭제 (분석 완료 후)
- 백그라운드 정리 (60분 이상 된 파일)
- 저장소 통계 추적

**사용 예시**:
```python
from app.temp_storage import temp_storage

# Context manager 사용 (자동 삭제)
with temp_storage.temporary_video(video_path) as temp_path:
    result = analyze_video(temp_path)
# 여기서 자동으로 파일 삭제됨
```

### 2. AI 분석 모듈 (`app/ai_analyzer.py`)

**목적**: 동영상 → 텍스트 변환 (AI 분석)

**구현된 Analyzer**:
- **MockVideoAnalyzer**: 개발/테스트용 (현재 활성)
- **OpenAIVideoAnalyzer**: OpenAI Vision API 용 (Placeholder)
- **BaseVideoAnalyzer**: 확장 가능한 추상 클래스

**분석 결과** (VideoAnalysisResult):
- `transcript`: 음성 → 텍스트 (Speech-to-Text)
- `description`: AI 생성 설명
- `summary`: 요약
- `keywords`: 키워드 추출
- `detected_objects`: 객체 감지 결과
- `detected_text`: OCR 텍스트
- `sentiment`: 감정 분석

**사용 예시**:
```python
from app.ai_analyzer import analyze_and_cleanup

# 분석 후 자동 삭제
result = analyze_and_cleanup(video_path)
print(result.summary)  # AI 생성 요약
```

### 3. Instagram Graph API 지원 (`app/platforms/instagram_graph.py`)

**목적**: 공식 Meta API를 통한 합법적 Instagram 접근

**특징**:
- OAuth 2.0 인증
- 비즈니스/크리에이터 계정 전용
- 자신의 콘텐츠만 접근 가능
- Rate Limit: 200 calls/hour

**설정 가이드**: `/docs/INSTAGRAM_GRAPH_API_SETUP.md` 참조

## 🌐 API 엔드포인트

### 1. AI 분석 워크플로우 (동영상용)

**POST `/api/analyze`**

합법적인 AI 분석: 다운로드 → 분석 → 삭제

**Request**:
```json
{
  "url": "https://www.youtube.com/shorts/RN4U9Gw-NZ8"
}
```

**Response**:
```json
{
  "status": "success",
  "platform": "youtube",
  "analysis": {
    "video_path": "/downloads/temp/...",
    "summary": "[MOCK] 동영상 요약...",
    "description": "[MOCK] AI 생성 설명...",
    "keywords": ["키워드1", "키워드2"],
    "analyzed_at": "2025-11-05T12:00:00Z"
  },
  "note": "Video was analyzed and deleted (fair use compliance)"
}
```

**특징**:
- ✅ Fair Use 준수 (transformative use)
- ✅ 원본 파일 즉시 삭제
- ✅ 텍스트 분석 결과만 반환
- ⚠️ 동영상 파일만 지원 (사진은 webview 사용)

### 2. 웹뷰 URL 반환 (사진/썸네일용)

**GET `/api/media/webview?url={sns_url}`**

다운로드 없이 embed URL 반환

**Request**:
```
GET /api/media/webview?url=https://www.instagram.com/p/ABC123/
```

**Response**:
```json
{
  "status": "success",
  "platform": "instagram",
  "identifier": "ABC123",
  "original_url": "https://www.instagram.com/p/ABC123/",
  "guidance": {
    "photos_thumbnails": "Use Instagram embed API or direct URLs in webview",
    "videos": "Use /api/analyze endpoint for AI analysis workflow",
    "note": "For webview display, embed original URLs directly without downloading"
  },
  "instagram_embed_url": "https://www.instagram.com/p/ABC123/embed",
  "youtube_embed_url": null
}
```

**사용 시나리오**:
```html
<!-- Instagram 사진/캐러셀 -->
<iframe src="https://www.instagram.com/p/ABC123/embed"
        width="400" height="480" frameborder="0">
</iframe>

<!-- YouTube 썸네일 -->
<img src="https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg">
```

### 3. 임시 저장소 통계

**GET `/api/temp-storage/stats`**

임시 저장소 상태 모니터링

**Response**:
```json
{
  "status": "success",
  "storage": {
    "total_files": 0,
    "total_dirs": 0,
    "total_size_bytes": 0,
    "total_size_mb": 0,
    "base_dir": "/downloads/temp"
  },
  "cleanup": {
    "enabled": true,
    "cleanup_after_seconds": 3600,
    "cleanup_after_minutes": 60
  }
}
```

## ⚖️ 법적 근거 (Legal Basis)

### Fair Use (공정 이용) 원칙

이 시스템은 미국 저작권법 Section 107의 Fair Use 원칙을 따릅니다:

1. **목적 및 성격** (Purpose and Character)
   - ✅ **Transformative Use**: 원본 동영상 → AI 분석 텍스트 (변형적 사용)
   - ✅ **비상업적 분석**: 교육, 연구, 분석 목적
   - ✅ **원본과 다른 형식**: 비디오 → 텍스트 요약

2. **저작물의 성격** (Nature of Work)
   - ✅ 공개된 SNS 콘텐츠 (Public social media posts)
   - ✅ 사실적 정보 위주

3. **사용된 부분의 양과 중요성** (Amount Used)
   - ✅ 분석 목적으로 필요한 최소한만 사용
   - ✅ 원본 파일 즉시 삭제 (No redistribution)

4. **시장 영향** (Market Effect)
   - ✅ 원저작물 시장에 영향 없음 (분석 결과만 사용)
   - ✅ 재배포 없음 (No file sharing or public access)

### 구현된 보호 조치

```python
# 1. 임시 저장만 허용
temp_storage = TemporaryStorage(cleanup_after_minutes=60)

# 2. 분석 후 즉시 삭제
analyze_and_cleanup(video_path)  # 자동 삭제

# 3. 텍스트만 저장
result.to_text()  # 원본 파일 없음
```

## 🚀 사용 가이드

### 시나리오 1: YouTube Shorts AI 분석

```bash
# 1. 동영상 AI 분석 (다운로드 → 분석 → 삭제)
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/shorts/RN4U9Gw-NZ8"
  }'

# Response: 분석 결과 (텍스트만)
{
  "status": "success",
  "analysis": {
    "summary": "...",
    "keywords": [...],
    "transcript": "..."
  },
  "note": "Video was analyzed and deleted"
}
```

### 시나리오 2: Instagram 사진 웹뷰 표시

```bash
# 1. Embed URL 획득 (다운로드 없음)
curl "http://localhost:8000/api/media/webview?url=https://www.instagram.com/p/ABC123/"

# Response: Embed URL
{
  "instagram_embed_url": "https://www.instagram.com/p/ABC123/embed"
}

# 2. 웹뷰에 직접 표시 (서버 저장 없음)
<iframe src="https://www.instagram.com/p/ABC123/embed"></iframe>
```

### 시나리오 3: Instagram Graph API (비즈니스 계정)

```bash
# 1. Access Token 설정 (.env 파일)
INSTAGRAM_GRAPH_API_TOKEN=your_token_here

# 2. 자신의 미디어 목록 조회
curl "https://graph.facebook.com/v18.0/me/media?access_token={TOKEN}"

# 3. 특정 미디어 다운로드 및 분석
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/reel/YOUR_REEL/"
  }'
```

## 🔮 향후 개선 사항

### AI Analyzer 실제 구현

현재 MockVideoAnalyzer 대신 실제 AI 서비스 연동:

**옵션 1: OpenAI Vision API**
```python
class OpenAIVideoAnalyzer(BaseVideoAnalyzer):
    def analyze(self, video_path: Path):
        # OpenAI Vision API 호출
        # GPT-4 Vision으로 프레임 분석
        # Whisper API로 음성 → 텍스트
        pass
```

**옵션 2: Anthropic Claude**
```python
class ClaudeVideoAnalyzer(BaseVideoAnalyzer):
    def analyze(self, video_path: Path):
        # Claude API로 프레임 분석
        # 텍스트 추출 및 요약
        pass
```

**옵션 3: 로컬 AI 모델**
```python
class LocalVideoAnalyzer(BaseVideoAnalyzer):
    def analyze(self, video_path: Path):
        # YOLO/CLIP으로 객체 감지
        # Whisper로 음성 인식
        # 로컬에서 처리 (비용 절감)
        pass
```

### 자동 토큰 갱신

Instagram Graph API 장기 토큰 자동 갱신:

```python
# app/instagram_token_manager.py
class TokenManager:
    def refresh_long_lived_token(self):
        # 60일마다 자동 갱신
        pass
```

### 배치 처리

여러 URL 동시 처리:

```python
@app.post("/api/analyze/batch")
async def analyze_batch(urls: List[str]):
    # 병렬 처리로 효율성 향상
    pass
```

## 📊 모니터링

### 저장소 사용량 확인

```bash
# 임시 저장소 통계
curl http://localhost:8000/api/temp-storage/stats

# 응답:
{
  "total_files": 0,
  "total_size_mb": 0,
  "cleanup_after_minutes": 60
}
```

### 로그 모니터링

```bash
# 서버 로그 확인
tail -f logs/app.log | grep "AI analysis"

# 출력 예시:
INFO - Processing AI analysis request for URL: ...
INFO - Deleted video after analysis: /downloads/temp/...
```

## 🛡️ 보안 고려사항

1. **Rate Limiting**
   - 기본: 10 requests/minute per IP
   - 조정 가능: `.env` 파일에서 `RATE_LIMIT_PER_MINUTE` 설정

2. **토큰 보안**
   ```bash
   # .env 파일은 절대 커밋하지 않기
   echo ".env" >> .gitignore

   # 토큰 권한 최소화
   INSTAGRAM_GRAPH_API_TOKEN=only_required_permissions
   ```

3. **임시 파일 정리**
   - 60분 이상 된 파일 자동 삭제
   - 서버 재시작 시 전체 정리
   - 디스크 사용량 모니터링

## 📚 참고 자료

- [Fair Use - US Copyright Office](https://www.copyright.gov/fair-use/)
- [Instagram Graph API Docs](https://developers.facebook.com/docs/instagram-api)
- [Transformative Use in AI](https://www.law.cornell.edu/wex/transformative_use)
- [YouTube Data API Terms](https://developers.google.com/youtube/terms/api-services-terms-of-service)

## ✅ 완료 체크리스트

- [x] Instagram Graph API 통합 (비즈니스 계정)
- [x] 동영상 임시 다운로드 + 자동 삭제 시스템
- [x] AI 분석 모듈 (동영상 → 텍스트) - Mock 구현
- [x] 웹뷰용 미디어 URL 반환 (사진/썸네일)
- [x] YouTube Shorts 다운로드 및 분석 지원
- [ ] 실제 AI Analyzer 구현 (OpenAI/Claude)
- [ ] 자동 토큰 갱신 시스템
- [ ] 배치 처리 기능
- [ ] 프로덕션 배포 설정
