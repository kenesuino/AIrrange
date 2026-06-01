"""
AI Provider Manager - Multi-Provider AI Support
Supports: Google Gemini, OpenAI, OpenRouter, xAI (Grok), and custom OpenAI-compatible endpoints
Models are fetched dynamically from each provider's API.
"""

import os
import json
import base64
import requests
from pathlib import Path
from abc import ABC, abstractmethod

# Provider configurations (models will be fetched dynamically)
PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models_endpoint": "/models",
        "requires_key": True
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models_endpoint": "/models",
        "requires_key": True
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "models_endpoint": "/models",
        "requires_key": True
    },
    "xai": {
        "name": "xAI (Grok)",
        "base_url": "https://api.x.ai/v1",
        "models_endpoint": "/models",
        "requires_key": True
    },
    "custom": {
        "name": "Custom (OpenAI-Compatible)",
        "base_url": "",
        "models_endpoint": "/models",
        "requires_key": True
    }
}

# Fallback models if API fetch fails
FALLBACK_MODELS = {
    "gemini": [
        {"id": "gemini-3-flash-preview", "name": "Gemini 3.0 Flash (Preview)", "vision": True},
        {"id": "gemini-3-pro-preview", "name": "Gemini 3.0 Pro (Preview)", "vision": True},
        {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash", "vision": True},
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "vision": True},
        {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "vision": True},
    ],
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o", "vision": True},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "vision": True},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "vision": True},
    ],
    "openrouter": [
        {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "vision": True},
        {"id": "google/gemini-pro-1.5", "name": "Gemini 1.5 Pro", "vision": True},
        {"id": "openai/gpt-4o", "name": "GPT-4o", "vision": True},
    ],
    "xai": [
        {"id": "grok-2-vision-1212", "name": "Grok 2 Vision", "vision": True},
        {"id": "grok-2-1212", "name": "Grok 2", "vision": False},
    ],
    "custom": []
}


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def generate(self, prompt: str, images: list = None) -> str:
        """Generate a response from the AI."""
        pass
    
    @abstractmethod
    def test_connection(self) -> dict:
        """Test the API connection."""
        pass


class GeminiProvider(AIProvider):
    """Google Gemini API provider."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key
        self.model = model
        self.base_url = PROVIDERS["gemini"]["base_url"]
    
    def generate(self, prompt: str, images: list = None) -> str:
        """Generate content using Gemini API."""
        if not self.api_key:
            raise Exception("API key not configured. Please add your Gemini API key in Settings.")
        
        import google.generativeai as genai
        
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        
        if images:
            # Vision request
            import PIL.Image
            parts = [prompt]
            for img_path in images[:3]:  # Max 3 images
                try:
                    img = PIL.Image.open(img_path)
                    parts.append(img)
                except Exception as e:
                    continue
            response = model.generate_content(parts)
        else:
            response = model.generate_content(prompt)
        
        return response.text
    
    def test_connection(self) -> dict:
        """Test Gemini API connection."""
        try:
            if not self.api_key:
                return {"success": False, "message": "API key not configured"}
            
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            response = model.generate_content("Say 'OK' if you can read this.")
            return {"success": True, "message": f"Connected to {self.model}"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def fetch_models(api_key: str) -> list:
        """Fetch available models from Gemini API."""
        if not api_key:
            return []
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            models = []
            for model in genai.list_models():
                # Filter for generateContent supported models
                if 'generateContent' in model.supported_generation_methods:
                    model_id = model.name.replace('models/', '')
                    # Skip embedding and other non-chat models
                    if 'embedding' in model_id.lower() or 'aqa' in model_id.lower():
                        continue
                    # Check if it's a vision model
                    is_vision = 'vision' in model_id.lower() or 'pro' in model_id.lower() or 'flash' in model_id.lower()
                    models.append({
                        "id": model_id,
                        "name": model.display_name,
                        "vision": is_vision
                    })
            
            # Sort by version (3.0 > 2.0 > 1.5 > 1.0), then by name
            def sort_key(m):
                name = m['id'].lower()
                if 'gemini-3' in name or '3-pro' in name or '3-flash' in name:
                    return (0, m['name'])
                elif 'gemini-2' in name or '2.0' in name or '2-' in name:
                    return (1, m['name'])
                elif 'gemini-1.5' in name or '1.5' in name:
                    return (2, m['name'])
                elif 'gemini-1' in name or '1.0' in name:
                    return (3, m['name'])
                else:
                    return (4, m['name'])
            
            models.sort(key=sort_key)
            
            return models[:25]  # Limit to top 25
        except Exception as e:
            print(f"Error fetching Gemini models: {e}")
            return FALLBACK_MODELS.get("gemini", [])


class OpenAICompatibleProvider(AIProvider):
    """OpenAI-compatible API provider (works with OpenAI, OpenRouter, xAI, etc.)."""
    
    def __init__(self, api_key: str, model: str, base_url: str, 
                 extra_headers: dict = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/') if base_url else ""
        self.extra_headers = extra_headers or {}
    
    def generate(self, prompt: str, images: list = None) -> str:
        """Generate content using OpenAI-compatible API."""
        if not self.api_key:
            raise Exception("API key not configured. Please add your API key in Settings.")
        if not self.base_url:
            raise Exception("Base URL not configured.")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers
        }
        
        messages = []
        
        if images:
            # Vision request with images
            content = [{"type": "text", "text": prompt}]
            for img_path in images[:3]:
                try:
                    with open(img_path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode()
                    ext = Path(img_path).suffix.lower().replace('.', '')
                    if ext == 'jpg':
                        ext = 'jpeg'
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{ext};base64,{img_data}"
                        }
                    })
                except Exception:
                    continue
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    def test_connection(self) -> dict:
        """Test API connection."""
        try:
            if not self.api_key:
                return {"success": False, "message": "API key not configured"}
            response = self.generate("Say 'OK' if you can read this.")
            return {"success": True, "message": f"Connected to {self.model}"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def fetch_models(api_key: str, base_url: str, provider_id: str, 
                     extra_headers: dict = None) -> list:
        """Fetch available models from OpenAI-compatible API."""
        if not api_key or not base_url:
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                **(extra_headers or {})
            }
            
            response = requests.get(
                f"{base_url.rstrip('/')}/models",
                headers=headers,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"Error fetching models: {response.status_code}")
                return FALLBACK_MODELS.get(provider_id, [])
            
            data = response.json()
            models = []
            
            # Parse based on provider
            if provider_id == "openrouter":
                # OpenRouter returns models in 'data' array
                for m in data.get("data", []):
                    model_id = m.get("id", "")
                    # Filter for popular/useful models
                    if any(x in model_id.lower() for x in ['gpt-4', 'claude', 'gemini', 'llama', 'deepseek', 'mistral']):
                        models.append({
                            "id": model_id,
                            "name": m.get("name", model_id),
                            "vision": "vision" in model_id.lower() or "4o" in model_id.lower()
                        })
            else:
                # Standard OpenAI format
                for m in data.get("data", []):
                    model_id = m.get("id", "")
                    # Filter for chat models
                    if provider_id == "openai":
                        if any(x in model_id for x in ['gpt-4', 'gpt-3.5', 'o1', 'o3']):
                            models.append({
                                "id": model_id,
                                "name": model_id,
                                "vision": "vision" in model_id or "4o" in model_id or "o1" in model_id
                            })
                    elif provider_id == "xai":
                        if 'grok' in model_id.lower():
                            models.append({
                                "id": model_id,
                                "name": model_id,
                                "vision": "vision" in model_id.lower()
                            })
                    else:
                        # Custom provider - show all
                        models.append({
                            "id": model_id,
                            "name": model_id,
                            "vision": "vision" in model_id.lower()
                        })
            
            # Sort alphabetically
            models.sort(key=lambda x: x['name'])
            
            return models[:30] if models else FALLBACK_MODELS.get(provider_id, [])
            
        except Exception as e:
            print(f"Error fetching models: {e}")
            return FALLBACK_MODELS.get(provider_id, [])


class ProviderManager:
    """Manages AI providers and model selection."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.provider = None
        self._init_provider()
    
    def _load_config(self) -> dict:
        """Load configuration from file."""
        default = {
            "provider": "gemini",
            "model": "gemini-2.0-flash-exp",
            "api_keys": {},
            "custom_base_url": ""
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    saved = json.load(f)
                    # Merge with defaults
                    for key in default:
                        if key not in saved:
                            saved[key] = default[key]
                    return saved
            except:
                return default
        return default
    
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _init_provider(self):
        """Initialize the current provider."""
        provider_id = self.config.get("provider", "gemini")
        model = self.config.get("model", "gemini-2.0-flash-exp")
        api_key = self.config.get("api_keys", {}).get(provider_id, "")
        
        # Also check environment variable
        if not api_key:
            env_vars = {
                "gemini": "GEMINI_API_KEY",
                "openai": "OPENAI_API_KEY",
                "openrouter": "OPENROUTER_API_KEY",
                "xai": "XAI_API_KEY"
            }
            api_key = os.environ.get(env_vars.get(provider_id, ""), "")
        
        if provider_id == "gemini":
            self.provider = GeminiProvider(api_key, model)
        else:
            base_url = PROVIDERS.get(provider_id, {}).get("base_url", "")
            if provider_id == "custom":
                base_url = self.config.get("custom_base_url", "")
            
            extra_headers = {}
            if provider_id == "openrouter":
                extra_headers["HTTP-Referer"] = "https://ai-file-sorter.local"
                extra_headers["X-Title"] = "AI File Sorter"
            
            self.provider = OpenAICompatibleProvider(
                api_key, model, base_url, extra_headers
            )
    
    def generate(self, prompt: str, images: list = None) -> str:
        """Generate content using current provider."""
        return self.provider.generate(prompt, images)
    
    def test_connection(self) -> dict:
        """Test current provider connection."""
        return self.provider.test_connection()
    
    def get_providers(self) -> dict:
        """Get list of available providers."""
        return PROVIDERS
    
    def get_models(self, provider_id: str = None, api_key: str = None) -> list:
        """Fetch models dynamically from provider API."""
        if provider_id is None:
            provider_id = self.config.get("provider", "gemini")
        
        # Get API key
        if api_key is None:
            api_key = self.config.get("api_keys", {}).get(provider_id, "")
        
        if not api_key:
            return []  # No API key, can't fetch models
        
        if provider_id == "gemini":
            return GeminiProvider.fetch_models(api_key)
        else:
            base_url = PROVIDERS.get(provider_id, {}).get("base_url", "")
            if provider_id == "custom":
                base_url = self.config.get("custom_base_url", "")
            
            extra_headers = {}
            if provider_id == "openrouter":
                extra_headers["HTTP-Referer"] = "https://ai-file-sorter.local"
                extra_headers["X-Title"] = "AI File Sorter"
            
            return OpenAICompatibleProvider.fetch_models(
                api_key, base_url, provider_id, extra_headers
            )
    
    def get_current_settings(self) -> dict:
        """Get current settings (with masked API key)."""
        provider_id = self.config.get("provider", "gemini")
        api_key = self.config.get("api_keys", {}).get(provider_id, "")
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "Not set"
        
        return {
            "provider": provider_id,
            "provider_name": PROVIDERS.get(provider_id, {}).get("name", "Unknown"),
            "model": self.config.get("model", ""),
            "api_key_masked": masked_key,
            "custom_base_url": self.config.get("custom_base_url", "")
        }
    
    def update_settings(self, provider: str = None, model: str = None, 
                       api_key: str = None, custom_base_url: str = None) -> dict:
        """Update settings and reinitialize provider."""
        if provider:
            self.config["provider"] = provider
        if model:
            self.config["model"] = model
        if api_key is not None:
            if "api_keys" not in self.config:
                self.config["api_keys"] = {}
            current_provider = self.config.get("provider", "gemini")
            self.config["api_keys"][current_provider] = api_key
        if custom_base_url is not None:
            self.config["custom_base_url"] = custom_base_url
        
        self._save_config()
        self._init_provider()
        
        return {"success": True, "settings": self.get_current_settings()}
    
    def supports_vision(self) -> bool:
        """Check if current model supports vision."""
        provider_id = self.config.get("provider", "gemini")
        model_id = self.config.get("model", "")
        
        # Get fresh model list
        models = self.get_models(provider_id)
        for m in models:
            if m["id"] == model_id:
                return m.get("vision", False)
        return False
