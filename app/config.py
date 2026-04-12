from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="NEMO_")

    # Database
    database_url: str = "postgresql+asyncpg://nemo:nemo@localhost:5432/nemoflow"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Scoring
    score_decay_halflife_days: float = 3.5
    bayesian_alpha_prior: float = 5.0
    bayesian_beta_prior: float = 1.0
    max_reports_per_query: int = 10000
    cache_ttl_hot: int = 300
    cache_ttl_cold: int = 60
    hot_threshold_reports_7d: int = 100

    # Rate limiting
    free_daily_limit: int = 100
    payg_free_daily_calls: int = 100            # Free grant before metering kicks in
    payg_daily_hard_cap: int = 100000           # Safety cap to prevent runaway agent bills
    pro_monthly_limit: int = 10000              # Pro is now a monthly quota
    enterprise_daily_limit: int = 100000
    per_ip_per_minute: int = 60

    # PAYG pricing (cents per overage call, surfaced in /pricing and audit logs)
    payg_price_cents: float = 0.8               # $0.008 per assessment

    # Anti-gaming
    max_reports_per_fingerprint_per_tool_per_day: int = 100

    # Anthropic (for on-demand tool assessment)
    anthropic_api_key: str = ""

    # Email (SendGrid)
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "bleep@nemoflow.com"
    sales_inbox_email: str = "sales@nemoflow.ai"

    # Stripe billing
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = "price_1TL1NeIXqsfJNwTofPK44WYh"  # Flat $29/mo
    stripe_payg_price_id: str = ""                               # Metered USD price (per-call)
    stripe_payg_meter_event_name: str = "nemoflow_assessment"    # Stripe billing meter event_name
    pro_price_display: str = "$29"
    pro_price_currency_symbol: str = "$"


settings = Settings()
