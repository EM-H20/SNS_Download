# Downloads 폴더 구조 설명

## 📁 기본 구조

```
downloads/
└── {shortcode}/              # Instagram shortcode로 폴더 생성
    ├── {날짜}_{shortcode}.mp4    # 비디오 파일
    └── {날짜}_{shortcode}.jpg    # 썸네일 이미지
```

## 📝 실제 예시

### 예시 1: Reels 다운로드
```
downloads/
└── CzXyZ123abc/
    ├── 2024-11-04_CzXyZ123abc.mp4    # 비디오 (실제 Reels 영상)
    └── 2024-11-04_CzXyZ123abc.jpg    # 썸네일 (첫 프레임)
```

**파일 정보:**
- 비디오: MP4 형식, 원본 화질 (1080x1920 등)
- 썸네일: JPG 형식, 영상 첫 프레임
- 날짜: YYYY-MM-DD 형식 (다운로드 날짜)

### 예시 2: 여러 Reels 다운로드
```
downloads/
├── ABC_123-xyz/
│   ├── 2024-11-04_ABC_123-xyz.mp4
│   └── 2024-11-04_ABC_123-xyz.jpg
├── DEF_456-uvw/
│   ├── 2024-11-04_DEF_456-uvw.mp4
│   └── 2024-11-04_DEF_456-uvw.jpg
└── GHI_789-rst/
    ├── 2024-11-05_GHI_789-rst.mp4
    └── 2024-11-05_GHI_789-rst.jpg
```

## 🔄 다운로드 프로세스

### 1. 요청
```bash
POST /api/download
{
  "url": "https://www.instagram.com/reel/CzXyZ123abc/"
}
```

### 2. 서버 처리
1. URL에서 shortcode 추출: `CzXyZ123abc`
2. 폴더 생성: `downloads/CzXyZ123abc/`
3. Instaloader로 비디오 다운로드
4. 파일명 생성: `2024-11-04_CzXyZ123abc.mp4`

### 3. 응답
```json
{
  "status": "success",
  "video_url": "/downloads/CzXyZ123abc/2024-11-04_CzXyZ123abc.mp4",
  "thumbnail_url": "/downloads/CzXyZ123abc/2024-11-04_CzXyZ123abc.jpg",
  "metadata": {
    "shortcode": "CzXyZ123abc",
    "duration_seconds": 15,
    "width": 1080,
    "height": 1920,
    "size_bytes": 2458624
  }
}
```

## 🌐 파일 접근 방법

### 방법 1: 브라우저에서 직접 접근
```
http://localhost:8000/downloads/CzXyZ123abc/2024-11-04_CzXyZ123abc.mp4
```

### 방법 2: curl로 다운로드
```bash
curl -O http://localhost:8000/downloads/CzXyZ123abc/2024-11-04_CzXyZ123abc.mp4
```

### 방법 3: Python으로 다운로드
```python
import requests

response = requests.post(
    "http://localhost:8000/api/download",
    json={"url": "https://www.instagram.com/reel/CzXyZ123abc/"}
)

data = response.json()
video_url = f"http://localhost:8000{data['video_url']}"

# 비디오 파일 다운로드
video_response = requests.get(video_url)
with open("my_video.mp4", "wb") as f:
    f.write(video_response.content)
```

### 방법 4: JavaScript로 다운로드
```javascript
// 1. 다운로드 요청
const response = await fetch('http://localhost:8000/api/download', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    url: 'https://www.instagram.com/reel/CzXyZ123abc/'
  })
});

const data = await response.json();

// 2. 비디오 다운로드
const videoUrl = `http://localhost:8000${data.video_url}`;
const a = document.createElement('a');
a.href = videoUrl;
a.download = 'instagram_reel.mp4';
a.click();
```

## 📊 파일 크기 예상

| 화질/길이 | 파일 크기 (대략) |
|----------|----------------|
| 15초 Reels (1080p) | 2-5 MB |
| 30초 Reels (1080p) | 5-10 MB |
| 60초 Reels (1080p) | 10-20 MB |
| 썸네일 (JPG) | 100-500 KB |

## 🔧 파일명 형식 상세

### Instaloader 기본 형식
```
{날짜}_{shortcode}.{확장자}
```

### 예시
```
2024-11-04_CzXyZ123abc.mp4
│         │         │         │
│         │         │         └─ 확장자 (mp4, jpg)
│         │         └─────────── Instagram shortcode (11자)
│         └───────────────────── 언더스코어 구분자
└─────────────────────────────── 다운로드 날짜 (YYYY-MM-DD)
```

## 🗑️ 저장소 관리

### 수동 삭제
```bash
# 특정 Reels 삭제
rm -rf downloads/CzXyZ123abc/

# 전체 삭제
rm -rf downloads/*/
```

### 디스크 사용량 확인
```bash
# 전체 크기
du -sh downloads/

# 폴더별 크기
du -sh downloads/*/
```

### 자동 정리 스크립트 (예시)
```bash
#!/bin/bash
# 30일 이상 된 파일 삭제
find downloads/ -type f -mtime +30 -delete
```

## 📝 주의사항

### 1. 동일 Reels 재다운로드
- 같은 shortcode로 재다운로드하면 **폴더 내용이 덮어씌워집니다**
- 날짜가 바뀌면 새 파일명으로 저장됩니다

### 2. 파일 접근 권한
- 서버를 통해서만 접근 가능 (정적 파일 서빙)
- 직접 파일시스템 접근은 서버와 같은 머신에서만 가능

### 3. 저장 경로 변경
`.env` 파일 수정:
```bash
DOWNLOAD_DIR=./my_custom_folder
```

재시작 후 적용:
```bash
./run.sh
```

## 🧪 테스트 시나리오

### 시나리오 1: 다운로드 후 파일 확인
```bash
# 1. 다운로드 요청
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/reel/CzXyZ123abc/"}'

# 2. 폴더 확인
ls -lh downloads/CzXyZ123abc/

# 출력 예시:
# -rw-r--r-- 1 user staff 3.2M Nov  4 14:30 2024-11-04_CzXyZ123abc.mp4
# -rw-r--r-- 1 user staff 245K Nov  4 14:30 2024-11-04_CzXyZ123abc.jpg

# 3. 파일 재생 (macOS)
open downloads/CzXyZ123abc/2024-11-04_CzXyZ123abc.mp4
```

### 시나리오 2: 브라우저에서 다운로드
1. API 문서 열기: http://localhost:8000/docs
2. `/api/download` 엔드포인트 테스트
3. 응답에서 `video_url` 복사
4. 브라우저 주소창에 전체 URL 입력:
   ```
   http://localhost:8000/downloads/CzXyZ123abc/2024-11-04_CzXyZ123abc.mp4
   ```
5. 비디오 재생 또는 다운로드

## 🔍 파일 구조 코드 참조

### parser.py에서 shortcode 추출
```python
shortcode = ReelsURLParser.extract_shortcode(url)
# "https://instagram.com/reel/ABC123/" → "ABC123"
```

### downloader.py에서 폴더 생성
```python
target_dir = settings.download_dir / shortcode
# downloads/ABC123/
target_dir.mkdir(parents=True, exist_ok=True)
```

### downloader.py에서 파일 검색
```python
# Instaloader가 생성한 파일 찾기
video_files = list(target_dir.glob(f"*{shortcode}*.mp4"))
# downloads/ABC123/*ABC123*.mp4
```

## 📱 모바일 앱 연동 예시

```swift
// iOS Swift 예시
func downloadReels(url: String) async throws -> URL {
    // 1. 서버에 다운로드 요청
    let request = ["url": url]
    let response = try await apiClient.post("/api/download", json: request)

    // 2. video_url 가져오기
    let videoPath = response["video_url"] as! String
    let videoURL = URL(string: "http://localhost:8000\(videoPath)")!

    // 3. 로컬에 저장
    let data = try await URLSession.shared.data(from: videoURL).0
    let localURL = FileManager.default.temporaryDirectory
        .appendingPathComponent("reel.mp4")
    try data.write(to: localURL)

    return localURL
}
```

## 💡 프로덕션 환경 팁

### 1. CDN 사용
```python
# main.py에서 CDN URL 반환
video_url = f"https://cdn.example.com/downloads/{shortcode}/{filename}"
```

### 2. 클라우드 스토리지 (AWS S3)
```python
# downloader.py에 추가
import boto3

def upload_to_s3(file_path, bucket, key):
    s3 = boto3.client('s3')
    s3.upload_file(str(file_path), bucket, key)
    return f"https://{bucket}.s3.amazonaws.com/{key}"
```

### 3. 다운로드 후 자동 삭제
```python
# config.py에 추가
auto_delete_after_hours: int = 24

# 스케줄러로 주기적 삭제
```
