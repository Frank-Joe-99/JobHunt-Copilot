from pathlib import Path
import yaml
from core.state import UserProfile, JobPreferences, AppSettings

# project root dic
PROJECT_ROOT = Path(__file__).resolve().parents[1]

def load_user_profile(path: Path | None = None) -> UserProfile:
    """加载并校验用户个人主档案"""
    config_path = path or PROJECT_ROOT / "config" / "profile.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return UserProfile.model_validate(raw)

    
def load_job_preference(path: Path | None = None) -> JobPreferences:
    """加载并校验求职偏好配置"""
    config_path = path or PROJECT_ROOT / "config" / "preferences.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return JobPreferences.model_validate(raw)

def load_app_settings(path: Path | None = None) -> AppSettings:
    """加载并校验系统运行配置"""
    config_path = path or PROJECT_ROOT / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppSettings.model_validate(raw)
