# 빠른 시작 가이드

## 🚀 서버 실행 (5분 완료)

### 1단계: 의존성 설치
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2단계: 서버 실행
```bash
# 방법 1: 스크립트 사용 (권장)
./run.sh

# 방법 2: 직접 실행
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

서버 실행 확인: http://localhost:8000

## 📖 API 사용법

### API 문서 확인
- Swagger UI: http://localhost:8000/docs
- 상태 확인: http://localhost:8000/health

### 다운로드 요청 예시

**curl 사용:**
```bash
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/reel/ABC123/"
  }'
```

**Python requests 사용:**
```python
import requests

response = requests.post(
    "http://localhost:8000/api/download",
    json={"url": "https://www.instagram.com/reel/ABC123/"}
)

data = response.json()
print(f"Video URL: {data['video_url']}")
print(f"Thumbnail URL: {data['thumbnail_url']}")
```

**JavaScript fetch 사용:**
```javascript
fetch('http://localhost:8000/api/download', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    url: 'https://www.instagram.com/reel/ABC123/'
  })
})
.then(res => res.json())
.then(data => {
  console.log('Video:', data.video_url);
  console.log('Thumbnail:', data.thumbnail_url);
});
```

## 📊 응답 형식

### 성공 응답 (200)
```json
{
  "status": "success",
  "video_url": "/downloads/ABC123/2024-01-01_ABC123.mp4",
  "thumbnail_url": "/downloads/ABC123/2024-01-01_ABC123.jpg",
  "metadata": {
    "shortcode": "ABC123",
    "duration_seconds": 15,
    "width": 1080,
    "height": 1920,
    "size_bytes": 2458624,
    "download_timestamp": "2024-01-01T12:00:00"
  }
}
```

### 오류 응답
```json
{
  "status": "error",
  "error_type": "private_account",
  "message": "Cannot download from private account: @username",
  "details": {"username": "username"}
}
```

## ⚠️ 에러 코드

| 코드 | 타입 | 설명 | 해결 방법 |
|------|------|------|-----------|
| 400 | invalid_url | URL 형식 오류 | Instagram Reels URL 확인 |
| 403 | private_account | 비공개 계정 | 공개 계정만 다운로드 가능 |
| 404 | content_not_found | 콘텐츠 없음 | URL 확인 또는 삭제된 콘텐츠 |
| 429 | rate_limit_exceeded | 요청 한도 초과 | 잠시 후 재시도 |
| 500 | download_failed | 다운로드 실패 | 재시도 또는 로그 확인 |
| 503 | instagram_api_error | Instagram API 변경 | 개발자 확인 필요 |

## 🧪 테스트

### 단위 테스트 실행
```bash
source .venv/bin/activate
pytest tests/ -v
```

### API 테스트
```bash
# 상태 확인
curl http://localhost:8000/health

# 루트 엔드포인트
curl http://localhost:8000/
```

## 🔧 설정 변경

`.env` 파일 수정:
```bash
# 서버 포트 변경
SERVER_PORT=9000

# Rate limit 조정 (분당 요청 수)
RATE_LIMIT_PER_MINUTE=20

# 다운로드 디렉토리 변경
DOWNLOAD_DIR=./my_downloads
```

## 💡 프로덕션 배포

### 1. Gunicorn 사용 (권장)
```bash
pip install gunicorn
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### 2. Docker 사용
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

## 📝 중요 참고 사항

1. **법적 책임**: 공개 계정, 비상업적 용도로만 사용
2. **Rate Limiting**: Instagram 차단 방지를 위한 요청 제한
3. **저장소 관리**: downloads/ 디렉토리 정기적 정리 필요
4. **로그 모니터링**: 에러 발생 시 로그 확인

## 🐛 문제 해결

### 서버가 시작되지 않을 때
```bash
# 포트 사용 확인
lsof -i :8000

# 가상환경 재생성
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Instaloader 오류
```bash
# 최신 버전으로 업데이트
pip install --upgrade instaloader
```

### 다운로드 실패
1. Instagram URL이 공개 계정인지 확인
2. URL 형식 확인 (reel, p, tv 경로 지원)
3. 네트워크 연결 확인
4. Rate limit 확인 (429 에러)

## 📚 추가 리소스

- 전체 문서: [README.md](README.md)
- API 문서: http://localhost:8000/docs
- Instaloader 문서: https://instaloader.github.io/
