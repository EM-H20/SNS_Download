"""Instagram 계정 로테이션 및 관리 시스템.

다중 계정 랜덤 로테이션으로 차단 회피 및 시스템 안정성 향상.
"""

import logging
import random
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class InstagramAccount:
    """Instagram 계정 정보 및 상태 추적."""

    username: str
    password: str
    is_blocked: bool = False
    blocked_until: Optional[datetime] = None
    total_requests: int = 0
    failed_requests: int = 0
    last_used: Optional[datetime] = None

    def is_available(self) -> bool:
        """계정 사용 가능 여부 확인."""
        # 차단된 계정이고 차단 기간이 남아있으면 사용 불가
        if self.is_blocked and self.blocked_until:
            if datetime.now() < self.blocked_until:
                return False
            else:
                # 차단 기간 만료 - 복구
                self.is_blocked = False
                self.blocked_until = None
                logger.info(f"Account {self.username} unblocked (timeout expired)")

        return not self.is_blocked

    def mark_success(self):
        """성공한 요청 기록."""
        self.total_requests += 1
        self.last_used = datetime.now()
        # 성공 시 실패 카운터 리셋
        self.failed_requests = 0

    def mark_failure(self):
        """실패한 요청 기록."""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_used = datetime.now()

        # 연속 3회 실패 시 1시간 차단
        if self.failed_requests >= 3:
            self.is_blocked = True
            self.blocked_until = datetime.now() + timedelta(hours=1)
            logger.warning(
                f"Account {self.username} temporarily blocked due to {self.failed_requests} failures. "
                f"Unblocking at {self.blocked_until}"
            )

    def to_dict(self) -> Dict:
        """통계 딕셔너리 반환."""
        return {
            "username": self.username,
            "is_blocked": self.is_blocked,
            "blocked_until": self.blocked_until.isoformat() if self.blocked_until else None,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }


class InstagramAccountManager:
    """다중 Instagram 계정 로테이션 관리자.

    기능:
    - 랜덤 계정 선택 (차단 우회)
    - 계정 상태 추적 (차단/활성)
    - 자동 계정 복구 (차단 해제)
    - 통계 및 모니터링
    """

    def __init__(self, accounts: List[Dict[str, str]]):
        """계정 관리자 초기화.

        Args:
            accounts: [{"username": "user1", "password": "pass1"}, ...]
        """
        self.accounts: List[InstagramAccount] = [
            InstagramAccount(username=acc["username"], password=acc["password"])
            for acc in accounts
        ]

        if not self.accounts:
            logger.warning("No Instagram accounts configured - authentication disabled")
        else:
            logger.info(f"Instagram account manager initialized with {len(self.accounts)} accounts")

    def get_random_account(self) -> Optional[InstagramAccount]:
        """사용 가능한 계정 중 랜덤하게 선택.

        Returns:
            사용 가능한 계정 또는 None (모든 계정 차단 시)
        """
        available_accounts = [acc for acc in self.accounts if acc.is_available()]

        if not available_accounts:
            logger.error("All Instagram accounts are blocked or unavailable")
            return None

        # 랜덤 선택
        account = random.choice(available_accounts)
        logger.debug(f"Selected account: {account.username} (available: {len(available_accounts)}/{len(self.accounts)})")
        return account

    def get_least_used_account(self) -> Optional[InstagramAccount]:
        """가장 적게 사용된 계정 선택 (로드 밸런싱).

        Returns:
            사용 가능한 계정 또는 None
        """
        available_accounts = [acc for acc in self.accounts if acc.is_available()]

        if not available_accounts:
            logger.error("All Instagram accounts are blocked or unavailable")
            return None

        # 요청 수가 가장 적은 계정 선택
        account = min(available_accounts, key=lambda acc: acc.total_requests)
        logger.debug(f"Selected least used account: {account.username} (requests: {account.total_requests})")
        return account

    def mark_account_success(self, username: str):
        """계정 성공 기록."""
        for account in self.accounts:
            if account.username == username:
                account.mark_success()
                break

    def mark_account_failure(self, username: str):
        """계정 실패 기록 (차단 감지 시)."""
        for account in self.accounts:
            if account.username == username:
                account.mark_failure()
                break

    def get_stats(self) -> Dict:
        """전체 계정 통계 반환."""
        available = sum(1 for acc in self.accounts if acc.is_available())
        blocked = sum(1 for acc in self.accounts if acc.is_blocked)
        total_requests = sum(acc.total_requests for acc in self.accounts)

        return {
            "total_accounts": len(self.accounts),
            "available_accounts": available,
            "blocked_accounts": blocked,
            "total_requests": total_requests,
            "accounts": [acc.to_dict() for acc in self.accounts]
        }

    def has_available_accounts(self) -> bool:
        """사용 가능한 계정이 있는지 확인."""
        return any(acc.is_available() for acc in self.accounts)


# 싱글톤 인스턴스는 config.py에서 생성됨
account_manager: Optional[InstagramAccountManager] = None
