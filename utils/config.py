"""
Configuration module for loading secrets from Azure Key Vault
"""
from typing import Dict
from dotenv import load_dotenv
from utils.keyvault_client import get_secret

# Load environment variables from .env file (only for AZURE_KEY_VAULT_URL)
load_dotenv()


class Config:
    """
    Configuration class that loads values from Azure Key Vault
    """
    
    def get_openai_config(self) -> Dict[str, str]:
        """Get OpenAI/Azure OpenAI configuration"""
        return {
            "ENDPOINT": get_secret("openai-endpoint"),
            "API_KEY": get_secret("openai-key"),
            "MODEL": get_secret("llm-model"),
            "API_VERSION": get_secret("openai-api-version"),
        }
    
    def get_speech_config(self) -> Dict[str, str]:
        """Get Azure Speech Service configuration"""
        return {
            "region": get_secret("speech-service-region"),
            "subscription_key": get_secret("speech-service-key"),
            "endpoint": get_secret("speech-service-endpoint"),
        }
    
    def get_ai_agent_config(self) -> Dict[str, str]:
        """Get AI Agent configuration"""
        return {
            "PROJECT_CONNECTION_STRING": get_secret("PROJECT-CONNECTION-STRING"),
            "ai_agent_id": get_secret("ai-agent-id"),
            "BING_CONNECTION_NAME": get_secret("BING-CONNECTION-NAME"),
            "search_agent_llm": get_secret("search-agent-llm"),
        }
    
    def get_best_model(self) -> str:
        """Get best model identifier"""
        return get_secret("best-model")
    
    def get_app_insights_connection_string(self) -> str:
        """Get Azure Application Insights connection string"""
        return get_secret("app-insights-connection-string")


# Singleton instance
_config_instance = None


def get_config() -> Config:
    """Get the singleton Config instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
