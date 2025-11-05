# Universal SNS Media Downloader & AI Analysis API

FastAPI 기반 멀티 플랫폼 SNS 미디어 다운로더 및 AI 분석 서버

## 🎯 주요 기능

- **멀티 플랫폼 지원**: Instagram (Reels, Posts), YouTube (Shorts, Videos)
- **Instagram 인증 다운로드**: yt-dlp 기반 실제 콘텐츠 다운로드
- **파일 크기 제한**: 설정 가능한 최대 파일 크기 제한
- **AI 분석 워크플로우**: Fair Use 준수 (다운로드 → 분석 → 삭제)
- **임시 저장소 관리**: 자동 정리 시스템
- **Rate Limiting**: IP 기반 요청 제한
- **완전한 타입 안정성**: Pydantic V2 검증

## ⚠️ 법적 고지

**현재 Instagram 다운로드 방식의 법적 위험:**
- Instagram 인증 방식(yt-dlp)은 Meta API 약관 위반 가능성 존재
- **개인 연구/테스트 목적으로만 사용 권장**
- 상업적 서비스 출시 시 Instagram Graph API로 전환 필수
- YouTube 다운로드는 yt-dlp 공식 지원으로 문제없음

자세한 법적 분석: [docs/LEGAL_AI_ANALYSIS_WORKFLOW.md](docs/LEGAL_AI_ANALYSIS_WORKFLOW.md)

## 🚀 빠른 시작

### 1. 프로젝트 클론

```bash
git clone <repository-url>
cd SNS_download_python
```

### 2. Python 가상환경 생성 및 활성화

```bash
# Python 3.13 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화
source .venv/bin/activate  # macOS/Linux
# 또는
.venv\Scripts\activate  # Windows
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일 편집 (선택사항)
# Instagram 인증을 사용하려면 아래 항목 설정:
# INSTAGRAM_USERNAME=your_test_account
# INSTAGRAM_PASSWORD=your_password
```

### 5. 서버 실행

```bash
# 개발 서버 실행 (auto-reload 활성화)
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

서버 시작 완료: `http://localhost:8000`

### 6. API 문서 확인

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- API 정보: http://localhost:8000/

## 📖 API 엔드포인트

### 1. 다운로드 (POST `/api/download`)

SNS 미디어 다운로드 (영구 저장)

**요청:**
```bash
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/mini_chloe_pick/reel/DPv7R6REvzB/"}'
```

**응답:**
```json
{
  "status": "success",
  "media_url": "/downloads/DPv7R6REvzB/2025-11-05_DPv7R6REvzB.mp4",
  "media_type": "video",
  "thumbnail_url": "/downloads/DPv7R6REvzB/2025-11-05_DPv7R6REvzB_thumb.jpg",
  "metadata": {
    "shortcode": "DPv7R6REvzB",
    "duration_seconds": 6,
    "width": 750,
    "height": 1333,
    "size_bytes": 4949025
  }
}
```

### 2. AI 분석 (POST `/api/analyze`)

동영상 AI 분석 후 자동 삭제 (Fair Use 준수)

**요청:**
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/shorts/fl2Lqgk_7II"}'
```

**응답:**
```json
{
  "status": "success",
  "platform": "youtube",
  "analysis": {
    "summary": "[AI 생성 요약]",
    "description": "[AI 생성 설명]",
    "keywords": ["키워드1", "키워드2"]
  },
  "note": "Video was analyzed and deleted (fair use compliance)"
}
```

### 3. 웹뷰 URL (GET `/api/media/webview`)

다운로드 없이 embed URL 반환 (사진/썸네일용)

**요청:**
```bash
curl "http://localhost:8000/api/media/webview?url=https://www.instagram.com/p/ABC123/"
```

**응답:**
```json
{
  "status": "success",
  "platform": "instagram",
  "identifier": "ABC123",
  "instagram_embed_url": "https://www.instagram.com/p/ABC123/embed",
  "guidance": {
    "photos_thumbnails": "Use Instagram embed API or direct URLs in webview",
    "videos": "Use /api/analyze endpoint for AI analysis workflow"
  }
}
```

### 4. 임시 저장소 통계 (GET `/api/temp-storage/stats`)

**요청:**
```bash
curl http://localhost:8000/api/temp-storage/stats
```

### 5. 헬스 체크 (GET `/health`)

**요청:**
```bash
curl http://localhost:8000/health
```

## 🏗️ 프로젝트 구조

```
SNS_download_python/
├── app/
│   ├── main.py                    # FastAPI 애플리케이션
│   ├── config.py                  # 환경 설정
│   ├── models.py                  # Pydantic 모델
│   ├── exceptions.py              # 커스텀 예외
│   ├── downloader.py              # Instagram 다운로더
│   ├── parser.py                  # URL 파서
│   ├── universal_downloader.py    # 멀티 플랫폼 다운로더
│   ├── ai_analyzer.py             # AI 분석 모듈
│   ├── temp_storage.py            # 임시 저장소 관리
│   ├── metadata_storage.py        # 메타데이터 저장
│   └── platforms/
│       ├── base.py                # 플랫폼 베이스 클래스
│       ├── instagram.py           # Instagram 플랫폼
│       └── youtube.py             # YouTube 플랫폼
├── docs/
│   ├── IMPLEMENTATION_SUMMARY.md  # 구현 요약
│   ├── LEGAL_AI_ANALYSIS_WORKFLOW.md  # 법적 AI 분석 가이드
│   └── INSTAGRAM_GRAPH_API_SETUP.md   # Graph API 설정
├── tests/                         # 테스트 코드
├── downloads/                     # 다운로드 파일 저장소
├── .env                          # 환경 변수 (gitignore)
├── .env.example                  # 환경 변수 예시
├── requirements.txt              # Python 의존성
└── README.md                     # 이 파일
```

## ⚙️ 환경 설정 (.env)

```bash
# 서버 설정
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
ENVIRONMENT=development

# 저장소 설정
DOWNLOAD_DIR=./downloads
MAX_FILE_SIZE_MB=100

# Rate Limiting (분당 요청 수)
RATE_LIMIT_PER_MINUTE=10

# Instagram 인증 (선택사항)
# 경고: 테스트 계정 사용 권장 (메인 계정 사용 시 정지 위험)
INSTAGRAM_USERNAME=test.10777
INSTAGRAM_PASSWORD=golocal777

# AI API Keys (선택사항 - 현재 미사용)
GOOGLE_API_KEY=
UPSTAGE_API_KEY=

# Instagram Graph API (선택사항 - 비즈니스 계정용)
INSTAGRAM_GRAPH_API_TOKEN=
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
```

## 🎬 지원 플랫폼 및 URL 형식

### Instagram
- **Reels**: `https://www.instagram.com/reel/{shortcode}/`
- **Posts**: `https://www.instagram.com/p/{shortcode}/`
- **Username Reels**: `https://www.instagram.com/{username}/reel/{shortcode}/`
- **TV**: `https://www.instagram.com/tv/{shortcode}/`

### YouTube
- **Shorts**: `https://www.youtube.com/shorts/{video_id}`
- **Videos**: `https://www.youtube.com/watch?v={video_id}`
- **Short URL**: `https://youtu.be/{video_id}`

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest tests/ -v

# URL 파서 테스트
pytest tests/test_parser.py -v

# 특정 테스트 실행
pytest tests/test_parser.py::TestReelsURLParser::test_extract_shortcode -v
```

## 📊 사용 시나리오

### 시나리오 1: Instagram Reel 다운로드 (영구 저장)

```bash
# 1. Reel 다운로드
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/mini_chloe_pick/reel/DPv7R6REvzB/"}'

# 2. 다운로드된 파일 확인
ls downloads/DPv7R6REvzB/
# 출력:
# 2025-11-05_DPv7R6REvzB.mp4 (4.7MB)
# 2025-11-05_DPv7R6REvzB_thumb.jpg (296KB)
# DPv7R6REvzB_metadata.json (2.2KB)
```

### 시나리오 2: YouTube Shorts AI 분석 (임시 저장 → 삭제)

```bash
# 1. AI 분석 요청 (Fair Use 준수)
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/shorts/fl2Lqgk_7II"}'

# 워크플로우:
# - 동영상 임시 다운로드 (36MB)
# - AI 분석 실행
# - 텍스트 추출 (요약, 설명, 키워드)
# - 원본 동영상 자동 삭제
# - 분석 결과(텍스트)만 반환
```

### 시나리오 3: Instagram 사진 웹뷰 표시

```bash
# 1. Embed URL 요청
curl "http://localhost:8000/api/media/webview?url=https://www.instagram.com/p/ABC123/"

# 2. 웹뷰에서 표시 (다운로드 없음)
# <iframe src="https://www.instagram.com/p/ABC123/embed"></iframe>
```

## 🔧 문제 해결

### Instagram 다운로드 시 로고만 다운로드됨

**원인**: yt-dlp 인증이 먼저 실행되지 않음
**해결**: `app/downloader.py`에서 yt-dlp 인증 방식을 최우선으로 설정 (이미 적용됨)

### 파일 크기 제한 초과

**원인**: MAX_FILE_SIZE_MB 설정보다 큰 파일
**해결**: `.env`에서 `MAX_FILE_SIZE_MB` 값 증가

### Instagram 계정 정지 위험

**권장**:
- 테스트 계정 사용 (메인 계정 절대 사용 금지)
- 상업적 서비스는 Instagram Graph API로 전환 필수

### URL 형식 오류

**지원 형식 확인**:
- Instagram: `/reel/`, `/p/`, `/tv/`, `/{username}/reel/`
- YouTube: `/shorts/`, `/watch?v=`, `youtu.be/`

## 🏭 프로덕션 배포

### 환경 변수 설정

```bash
ENVIRONMENT=production
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

### Gunicorn으로 실행

```bash
# Gunicorn 설치
pip install gunicorn

# 4개 워커로 실행
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### 권장 사항

1. **리버스 프록시**: nginx/Caddy 사용
2. **프로세스 관리**: systemd/supervisor
3. **Rate Limiting**: nginx 레벨에서 추가 제한
4. **영구 저장소**: `/downloads` 디렉토리 볼륨 마운트
5. **모니터링**: `/health` 엔드포인트 활용

## 🛠️ 기술 스택

- **Framework**: FastAPI 0.104+
- **Server**: Uvicorn (ASGI)
- **Instagram**: yt-dlp (인증), Instaloader (fallback)
- **YouTube**: yt-dlp
- **Validation**: Pydantic V2
- **Rate Limiting**: SlowAPI
- **Testing**: pytest
- **Python**: 3.13+

## 📚 문서

- [구현 요약](docs/IMPLEMENTATION_SUMMARY.md) - 전체 구현 내역
- [법적 AI 분석 워크플로우](docs/LEGAL_AI_ANALYSIS_WORKFLOW.md) - Fair Use 가이드
- [Instagram Graph API 설정](docs/INSTAGRAM_GRAPH_API_SETUP.md) - 공식 API 사용법

## 🔐 보안 고려사항

1. **Instagram 인증 정보 보안**
   - `.env` 파일은 절대 커밋하지 않기
   - 테스트 계정만 사용

2. **Rate Limiting**
   - 기본 10 req/min (IP 기반)
   - `.env`에서 조정 가능

3. **파일 크기 제한**
   - 기본 100MB
   - 다운로드 전/후 검증

## 🤝 기여

이 프로젝트는 교육/연구 목적입니다. 기여 시:
- 법적 준수 유지
- 테스트 코드 포함
- 기존 코드 스타일 준수
- 문서 업데이트

## 📄 라이선스

교육 및 연구 목적. 상업적 사용 금지.

## 🔗 참고 자료

- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Instagram Terms of Service](https://help.instagram.com/581066165581870)
- [Meta API Terms](https://developers.facebook.com/terms)
