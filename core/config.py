from functools import lru_cache
import os
from pathlib import Path
import re
from typing import Any
import yaml
from core.state import UserProfile, JobPreferences, AppSettings

# project root dir
PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env_vars(value: Any) -> Any:
    """递归展开 YAML 中的 ${ENV_VAR}，未设置的变量保持原样。"""
    if isinstance(value, str):
        return _ENV_VAR_PATTERN.sub(
            lambda match: os.environ.get(match.group(1), match.group(0)),
            value,
        )
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env_vars(item) for key, item in value.items()}
    return value


@lru_cache(maxsize=16)
def _read_yaml_file(file_path_str: str) -> dict[str, Any]:
    """读取并缓存 YAML 配置文件解析结果，避免高频重复磁盘 I/O"""
    file_path = Path(file_path_str)
    if not file_path.exists():
        raise FileNotFoundError(f"配置文件未找到: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"配置文件内容为空: {file_path}")
    return _expand_env_vars(data)


def load_user_profile(path: Path | None = None) -> UserProfile:
    """加载并校验用户个人主档案"""
    config_path = path or PROJECT_ROOT / "config" / "profile.yaml"
    raw = _read_yaml_file(str(config_path.resolve()))
    return UserProfile.model_validate(raw)


def load_job_preference(path: Path | None = None) -> JobPreferences:
    """加载并校验求职偏好配置"""
    config_path = path or PROJECT_ROOT / "config" / "preferences.yaml"
    raw = _read_yaml_file(str(config_path.resolve()))
    return JobPreferences.model_validate(raw)


def load_app_settings(path: Path | None = None) -> AppSettings:
    """加载并校验系统运行配置"""
    config_path = path or PROJECT_ROOT / "config" / "settings.yaml"
    raw = _read_yaml_file(str(config_path.resolve()))
    return AppSettings.model_validate(raw)
