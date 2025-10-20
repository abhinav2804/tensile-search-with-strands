# services/dynamo_service.py
import requests
from app.utils.logger import logger


def get_user_data(user_id, config):
    """
    Fetch user data from an external API (DynamoDB proxy service).
    This uses a URL from config instead of AWS credentials.
    """
    try:
        # ✅ Build the full URL
        base_url = config["aws"]["dynamodb"]["base_url"].rstrip("/")
        url = f"{base_url}/users/{user_id}"

        logger.info(f"🌐 Fetching user data from: {url}")

        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to fetch user data: {response.status_code} {response.text}")
            return {}

        data = response.json()
        logger.info(f"✅ DynamoDB data fetched for user_id {user_id}")
        return data

    except Exception as e:
        logger.error(f"❌ Error fetching DynamoDB data: {e}")
        return {}
