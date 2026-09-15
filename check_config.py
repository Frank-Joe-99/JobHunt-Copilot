"""检查本地配置：uv run check_config.py。"""

from core.config import load_app_settings, load_job_preference, load_user_profile


def main() -> None:
    for filename, loader in (
        ("profile.yaml", load_user_profile),
        ("preferences.yaml", load_job_preference),
        ("settings.yaml", load_app_settings),
    ):
        loader()
        print(f"[OK] config/{filename}")


if __name__ == "__main__":
    main()
