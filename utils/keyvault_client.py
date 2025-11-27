"""
Azure Key Vault Client for retrieving secrets
"""
import os
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from typing import Optional
# import logging

# logger = logging.getLogger(__name__)


class KeyVaultClient:
    """
    Singleton client for Azure Key Vault access
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KeyVaultClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not KeyVaultClient._initialized:
            self.vault_url = os.environ.get("AZURE_KEY_VAULT_URL")
            if not self.vault_url:
                raise ValueError("AZURE_KEY_VAULT_URL environment variable is required")
            
            self.client = self._create_client()
            self._cache = {}
            KeyVaultClient._initialized = True

    def _create_client(self) -> SecretClient:
        """
        Create Key Vault client with DefaultAzureCredential
        """
        try:
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=self.vault_url, credential=credential)
            print(f"Connected to Key Vault: {self.vault_url}")
            return client
        except Exception as e:
            print(f"Failed to connect to Key Vault: {e}")
            raise

    def get_secret(self, secret_name: str, use_cache: bool = True) -> str:
        """
        Retrieve a secret from Azure Key Vault
        
        Args:
            secret_name: Name of the secret in Key Vault
            use_cache: Whether to use cached value if available
            
        Returns:
            Secret value as string
        """
        # Check cache first
        if use_cache and secret_name in self._cache:
            print(f"Retrieved secret '{secret_name}' from cache")
            return self._cache[secret_name]
        
        try:
            secret = self.client.get_secret(secret_name)
            self._cache[secret_name] = secret.value
            print(f"Retrieved secret '{secret_name}' from Key Vault")
            return secret.value
        except Exception as e:
            print(f"Failed to retrieve secret '{secret_name}': {e}")
            raise

    def refresh_cache(self):
        """Clear the cache to force fresh retrieval from Key Vault"""
        self._cache.clear()
        print("Key Vault cache cleared")


# Convenience function for easy access
def get_secret(secret_name: str, use_cache: bool = True) -> str:
    """
    Get a secret from Azure Key Vault
    
    Args:
        secret_name: Name of the secret in Key Vault
        use_cache: Whether to use cached value
        
    Returns:
        Secret value as string
    """
    client = KeyVaultClient()
    return client.get_secret(secret_name, use_cache)
