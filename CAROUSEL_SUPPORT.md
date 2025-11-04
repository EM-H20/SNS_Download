# 캐러셀(Carousel) 포스트 지원

## 📸 캐러셀 포스트란?

Instagram의 캐러셀 포스트는 하나의 게시물에 여러 장의 사진이나 동영상이 포함된 형식입니다.

**예시 URL:**
```
https://www.instagram.com/p/DO-u-YwD6Rt?img_index=11
```
- `DO-u-YwD6Rt` = 포스트 shortcode
- `?img_index=11` = 캐러셀의 11번째 아이템

## ⚠️ 현재 제한사항

### yt-dlp 기반 다운로드 (기본 설정)
- ✅ 단일 이미지/비디오 다운로드 가능
- ✅ 로그인 불필요
- ❌ **캐러셀 포스트는 첫 번째 항목만 다운로드**
- ❌ `?img_index=N` 파라미터 무시됨

**동작:**
```bash
# 캐러셀 포스트 요청
curl -X POST "http://localhost:8000/api/download" \
  -d '{"url": "https://www.instagram.com/p/DO-u-YwD6Rt?img_index=11"}'

# 결과: 11번째가 아닌 첫 번째 항목만 다운로드
```

## ✅ 캐러셀 전체 다운로드 방법

### 옵션 1: Instaloader 활성화 (권장)

**1단계: Instagram 계정 설정**

⚠️ **중요: 메인 계정 사용 금지!**
- 교육용/테스트 전용 계정 생성
- Instagram 계정 정지 위험 존재
- 2단계 인증(2FA) 비활성화 필요

**2단계: .env 파일 설정**

```bash
# Instagram Authentication (캐러셀 지원 활성화)
INSTAGRAM_USERNAME=your_test_account
INSTAGRAM_PASSWORD=your_test_password
```

**3단계: 서버 재시작**

```bash
./run.sh
```

**결과:**
```json
{
  "status": "success",
  "media_type": "carousel",
  "media_urls": [
    "/downloads/shortcode/image1.jpg",
    "/downloads/shortcode/image2.jpg",
    "/downloads/shortcode/image3.jpg"
  ]
}
```

### 옵션 2: 개별 항목 직접 다운로드

캐러셀의 각 항목을 개별적으로 다운로드하려면:

1. 브라우저에서 Instagram 포스트 열기
2. 원하는 이미지/비디오로 스와이프
3. 개발자 도구 (F12) 열기
4. 네트워크 탭에서 실제 미디어 URL 찾기
5. 해당 URL을 직접 다운로드

## 🔧 구현 상세

### 캐러셀 감지 로직

**[downloader.py:89-96](app/downloader.py#L89-L96)**

```python
# yt-dlp가 캐러셀을 'playlist' 타입으로 반환
if info.get('_type') == 'playlist' or info.get('entries'):
    logger.warning("Carousel post detected. Only first item downloaded.")
    logger.warning("Configure Instagram credentials for full support")
    # 첫 번째 항목만 사용
    if info.get('entries'):
        info = info['entries'][0]
```

### Instaloader 캐러셀 처리

**[downloader_instaloader.py:103-108](app/downloader_instaloader.py#L103-L108)**

```python
is_carousel = post.typename == 'GraphSidecar'

if is_carousel:
    media_type = "carousel"
    logger.info(f"Detected carousel with {post.mediacount} items")
    # Instaloader가 자동으로 모든 항목 다운로드
```

## 📊 비교표

| 기능 | yt-dlp (기본) | Instaloader (로그인) |
|------|--------------|---------------------|
| 단일 미디어 | ✅ 완전 지원 | ✅ 완전 지원 |
| 캐러셀 | ⚠️ 첫 항목만 | ✅ 전체 다운로드 |
| 로그인 필요 | ❌ 불필요 | ✅ 필수 |
| 공개 포스트 | ✅ 지원 | ✅ 지원 |
| 비공개 포스트 | ❌ 불가 | ✅ 가능 |
| 계정 정지 위험 | ❌ 없음 | ⚠️ 존재 |
| 속도 | ⚡ 빠름 | 🐌 보통 |

## 🎯 권장 사항

### 개인/교육 용도
- **단일 미디어만 필요**: 기본 설정 (yt-dlp) 사용
- **캐러셀 필요**: 테스트 계정으로 Instaloader 활성화

### 프로덕션 환경
- **기본적으로 yt-dlp 사용** (로그인 불필요)
- **캐러셀은 첫 항목만 제공하고 사용자에게 안내**
- **전체 캐러셀 필요 시 사용자에게 안내 메시지 표시:**
  ```
  "This is a carousel post with multiple items.
   Only the first item was downloaded.
   For full carousel support, contact the administrator."
  ```

## 🐛 문제 해결

### "Carousel detected" 경고가 나오는데 다운로드가 안 됨

**원인:** yt-dlp가 캐러셀의 첫 항목을 추출하지 못함

**해결책:**
1. Instaloader로 전환 (.env에 Instagram 계정 설정)
2. 또는 해당 포스트가 비공개인지 확인

### Instaloader 로그인 실패

**원인:** 2단계 인증(2FA) 활성화 또는 계정 보안 설정

**해결책:**
1. 2FA 비활성화
2. "의심스러운 로그인 시도" 알림 승인
3. 새 테스트 계정 생성

### 계정이 정지됨

**원인:** Instagram의 자동화 감지

**예방:**
- 요청 빈도 제한 (RATE_LIMIT_PER_MINUTE 낮추기)
- 메인 계정 절대 사용 금지
- 교육용 계정만 사용
- VPN 사용 고려

## 📚 관련 문서

- [Instagram API 제한사항](https://developers.facebook.com/docs/instagram-api)
- [yt-dlp 문서](https://github.com/yt-dlp/yt-dlp)
- [Instaloader 문서](https://instaloader.github.io/)
- [Instagram 이용 약관](https://help.instagram.com/581066165581870)

## 💡 개발 참고사항

캐러셀 지원을 완전히 구현하려면:

1. **인증 시스템 개선**
   - OAuth 2.0 구현
   - 사용자별 Instagram 계정 연동

2. **선택적 다운로드**
   - 캐러셀에서 특정 항목만 선택 다운로드
   - `?img_index=N` 파라미터 실제 처리

3. **하이브리드 접근**
   - 로그인 없을 때: 첫 항목 + 안내 메시지
   - 로그인 있을 때: 전체 캐러셀 다운로드

4. **사용자 경험 개선**
   - 캐러셀 미리보기 제공
   - 항목별 개별 다운로드 링크
