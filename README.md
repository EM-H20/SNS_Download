# Instagram Reels 다운로더 API

프로덕션급 Python FastAPI 서버로 Instagram Reels를 다운로드할 수 있습니다.

## ⚠️ 중요 법적 고지

**이 도구는 교육 목적으로만 사용됩니다.**

- ✅ **공개 계정**에서만 작동합니다
- ✅ **개인적, 비상업적 용도**로만 사용하세요
- ❌ Instagram 서비스 약관을 준수하세요
- ❌ 콘텐츠 재배포나 상업적 목적으로 사용하지 마세요
- ❌ 콘텐츠 제작자의 지적 재산권을 존중하세요

## 🎯 주요 기능

- **Instagram 인증 지원**: 계정 로그인으로 더 안정적인 다운로드
- **속도 제한**: 남용 방지 및 Instagram API 보호
- **다양한 URL 형식**: `/reel/`, `/p/`, `/tv/`, `username/reel/` URL 지원
- **강력한 에러 처리**: 다양한 실패 시나리오에 대한 명확한 에러 메시지
- **프로덕션 준비**: 종합적인 로깅, 헬스 체크, 모니터링
- **타입 안전성**: Pydantic 검증 및 타입 힌트 완비

## 🏗️ 아키텍처

```
app/
├── main.py          # FastAPI 애플리케이션 및 엔드포인트
├── downloader.py    # 핵심 다운로드 엔진 (yt-dlp)
├── parser.py        # URL 파싱 및 검증
├── models.py        # Pydantic 요청/응답 모델
├── config.py        # 설정 관리
└── exceptions.py    # 커스텀 예외 계층
```

**전략**: yt-dlp를 사용한 고품질 다운로드, Instagram 인증으로 안정성 향상

## 🚀 빠른 시작

### 1. 가상 환경 설정

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 또는
.venv\Scripts\activate  # Windows
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 Instagram 계정 정보 입력 (선택사항)
```

### 4. 서버 시작

```bash
# 직접 uvicorn으로 실행
python -m uvicorn app.main:app --reload

# 또는 스크립트 사용
chmod +x run.sh
./run.sh
```

서버는 `http://localhost:8000`에서 시작됩니다

## 📖 API 문서

### 인터랙티브 문서

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 엔드포인트

#### POST `/api/download`

Instagram Reels 비디오를 다운로드합니다.

**요청 본문:**
```json
{
  "url": "https://www.instagram.com/reel/ABC123/"
}
```

**성공 응답 (200):**
```json
{
  "status": "success",
  "media_url": "/downloads/ABC123/2025-11-05_ABC123.mp4",
  "thumbnail_url": "/downloads/ABC123/2025-11-05_ABC123_thumb.jpg",
  "metadata": {
    "shortcode": "ABC123",
    "duration_seconds": 15,
    "width": 1080,
    "height": 1920,
    "size_bytes": 2458624,
    "download_timestamp": "2025-11-05T12:00:00"
  },
  "caption": "비디오 설명...",
  "hashtags": ["hashtag1", "hashtag2"],
  "mentions": ["user1", "user2"]
}
```

**에러 응답:**

| 상태 코드 | 에러 타입 | 설명 |
|--------|------------|-------------|
| 400 | `invalid_url` | URL 형식이 잘못됨 |
| 403 | `private_account` | 비공개 계정의 콘텐츠 |
| 404 | `content_not_found` | 콘텐츠가 존재하지 않거나 삭제됨 |
| 429 | `rate_limit_exceeded` | 요청이 너무 많음, 나중에 재시도 |
| 500 | `download_failed` | 재시도 후에도 다운로드 실패 |
| 503 | `instagram_api_error` | Instagram API 구조 변경 |

#### GET `/health`

모니터링을 위한 헬스 체크

**응답:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-05T12:00:00",
  "checks": {
    "download_dir_writable": true,
    "downloader_initialized": true,
    "instagram_auth": true
  }
}
```

## 🧪 테스트

### 단위 테스트 실행

```bash
pytest tests/ -v
```

### URL 파서 테스트

```bash
pytest tests/test_parser.py -v
```

### curl을 이용한 수동 테스트

```bash
# Reels 비디오 다운로드
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/reel/ABC123/"
  }'

# 헬스 체크
curl http://localhost:8000/health
```

## 📊 설정

`.env` 파일을 편집하여 동작을 커스터마이즈하세요:

```bash
# 서버 설정
SERVER_HOST=127.0.0.1
SERVER_PORT=8000

# 저장소 설정
DOWNLOAD_DIR=./downloads
MAX_FILE_SIZE_MB=100

# 속도 제한 (분당 요청 수)
RATE_LIMIT_PER_MINUTE=10

# Instagram 설정
REQUEST_TIMEOUT_SECONDS=30
MAX_RETRIES=3

# Instagram 인증 (선택사항 - 더 안정적인 다운로드를 위해 권장)
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```

## 🔧 문제 해결

### 일부 콘텐츠만 다운로드됨 (로고만 받아짐)

**원인**: Instagram이 일부 콘텐츠에 대한 접근을 제한함
**해결책**: `.env` 파일에 Instagram 계정 정보를 추가하세요

### "Rate limit exceeded" 에러

**원인**: Instagram에 너무 많은 요청을 보냄
**해결책**: `RATE_LIMIT_PER_MINUTE` 값을 늘리거나 재시도 전에 대기

### 다운로드 후 비디오 파일을 찾을 수 없음

**원인**: yt-dlp 파일명 규칙이 변경됨
**해결책**: `app/downloader.py`의 파일명 패턴 확인

### 비공개 계정 에러

**예상된 동작**: 설계상 의도된 것입니다. API는 공개 계정에서만 작동합니다.

## 🏭 프로덕션 배포

### 권장 설정

1. **리버스 프록시**: uvicorn 앞에 nginx/caddy 사용
2. **프로세스 매니저**: 자동 재시작을 위해 systemd/supervisor 사용
3. **속도 제한**: 추가 보호를 위해 nginx 레벨에서 설정
4. **저장소**: `downloads/` 디렉토리에 영구 볼륨 마운트
5. **모니터링**: 가동 시간 모니터링을 위해 헬스 체크 엔드포인트 사용

### 환경 변수

```bash
ENVIRONMENT=production
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

### 프로덕션 서버로 실행

```bash
# 프로덕션 의존성 설치
pip install gunicorn

# gunicorn으로 실행 (4 워커)
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile -
```

## 🛠️ 기술 스택

- **프레임워크**: FastAPI 0.104+
- **서버**: Uvicorn (ASGI)
- **다운로드**: yt-dlp (Instagram 인증 지원)
- **검증**: Pydantic V2
- **속도 제한**: SlowAPI
- **테스트**: pytest

## 📝 개발 노트

### 코드 스타일

- **타입 힌트**: 모든 함수에 완전한 타입 어노테이션
- **독스트링**: 공개 API에 대한 Google 스타일 독스트링
- **주석**: 코드에서 의도가 명확하지 않은 경우에만 사용
- **에러 처리**: 특정 예외 타입 사용, bare except 금지

### 새 기능 추가하기

1. `app/exceptions.py`에 예외 타입 추가
2. `app/models.py`에 요청/응답 모델 추가
3. 각 모듈에 비즈니스 로직 구현
4. `app/main.py`에 엔드포인트 추가
5. `tests/`에 테스트 작성

## 🤝 기여하기

이것은 교육용 프로젝트입니다. 기여는 다음을 따라야 합니다:

- 법적 준수 유지
- 새 기능에 대한 테스트 포함
- 기존 코드 스타일 준수
- 문서 업데이트

## 📄 라이선스

교육용으로만 사용. 위의 법적 고지를 참조하세요.

## 🔗 참고 자료

- [yt-dlp 문서](https://github.com/yt-dlp/yt-dlp)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Instagram 서비스 약관](https://help.instagram.com/581066165581870)
