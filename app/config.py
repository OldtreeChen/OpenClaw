from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_maps_api_key: str = ""
    line_channel_secret: str = ""
    line_channel_access_token: str = ""
    line_reply_api_url: str = "https://api.line.me/v2/bot/message/reply"

    inline_api_key: str = ""
    inline_base_url: str = ""
    inline_create_path: str = "/api/reservations"
    inline_cancel_path: str = "/api/reservations/{reservation_id}/cancel"
    inline_auth_header: str = "Authorization"
    inline_auth_scheme: str = "Bearer"
    inline_timeout_seconds: float = Field(default=15.0, ge=1.0, le=120.0)

    eztable_api_key: str = ""
    eztable_base_url: str = ""
    eztable_create_path: str = "/api/reservations"
    eztable_cancel_path: str = "/api/reservations/{reservation_id}/cancel"
    eztable_auth_header: str = "Authorization"
    eztable_auth_scheme: str = "Bearer"
    eztable_timeout_seconds: float = Field(default=15.0, ge=1.0, le=120.0)

    google_places_text_search_url: str = "https://places.googleapis.com/v1/places:searchText"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
