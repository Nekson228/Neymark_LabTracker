from yandex_cloud_ml_sdk import YCloudML
from ..config import settings

def get_ycloud_sdk() -> YCloudML:
    """Initialize Yandex Cloud ML SDK client."""
    return YCloudML(
        folder_id=settings.yc_folder_id,
        auth=settings.yc_auth_token,
    )