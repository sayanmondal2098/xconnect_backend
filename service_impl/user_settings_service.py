from __future__ import annotations

from base_requests import UserSettings, UserSettingsResponse, UpdateUserSettingsRequest
from impl.db.session import SessionLocal
from impl.db.models import UserSetting


class UserSettingsService:
    """Persisted per-user settings.

    Minimal schema: theme + notifications.
    """

    def get(self, *, user_id: int) -> UserSettingsResponse:
        with SessionLocal() as db:
            row = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
            if not row:
                row = UserSetting(user_id=user_id, theme="dark", notifications=True)
                db.add(row)
                db.commit()
                db.refresh(row)

            return UserSettingsResponse(
                ok=True,
                settings=UserSettings(theme=row.theme or "dark", notifications=bool(row.notifications)),
            )

    def update(self, *, user_id: int, req: UpdateUserSettingsRequest) -> UserSettingsResponse:
        with SessionLocal() as db:
            row = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
            if not row:
                row = UserSetting(user_id=user_id, theme="dark", notifications=True)
                db.add(row)
                db.commit()
                db.refresh(row)

            if req.theme is not None:
                row.theme = (req.theme or "dark")[:30]
            if req.notifications is not None:
                row.notifications = bool(req.notifications)

            db.commit()
            db.refresh(row)

            return UserSettingsResponse(
                ok=True,
                settings=UserSettings(theme=row.theme or "dark", notifications=bool(row.notifications)),
            )
