"""
Ollama Service - Ollama AI modeline erişim sağlayan servis
"""

import asyncio
import aiohttp
from typing import Optional
from app.core.config import get_settings

settings = get_settings()


class OllamaService:
    """Ollama AI servisi"""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url if hasattr(settings, 'ollama_base_url') else "http://localhost:11434"
    
    async def chat(
        self, 
        prompt: str, 
        model: str = "codellama", 
        system: str = "", 
        temperature: float = 0.7
    ) -> str:
        """
        Ollama ile sohbet et
        
        Args:
            prompt: Model'e gönderilecek mesaj
            model: Kullanılacak model adı (varsayılan: codellama)
            system: Sistem mesajı (isteğe bağlı)
            temperature: Yaratıcılık seviyesi (0.0-1.0)
            
        Returns:
            Model'in yanıtı
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        if system:
            payload["system"] = system
        
        if temperature:
            payload["options"] = {"temperature": temperature}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API hatası: {error_text}")
                    
                    result = await response.json()
                    return result.get("response", "")
        except Exception as e:
            raise Exception(f"Ollama bağlantı hatası: {str(e)}")
    
    async def list_models(self) -> list:
        """
        Ollama'da mevcut olan modelleri listele
        
        Returns:
            Model listesi
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API hatası: {error_text}")
                    
                    result = await response.json()
                    return result.get("models", [])
        except Exception as e:
            raise Exception(f"Ollama bağlantı hatası: {str(e)}")
    
    async def generate(
        self, 
        prompt: str, 
        model: str = "codellama", 
        suffix: str = ""
    ) -> str:
        """
        Ollama ile metin üretimi
        
        Args:
            prompt: Üretim için prompt
            model: Kullanılacak model adı
            suffix: Metnin sonuna eklenecek suffix (isteğe bağlı)
            
        Returns:
            Üretilen metin
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        if suffix:
            payload["suffix"] = suffix
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API hatası: {error_text}")
                    
                    result = await response.json()
                    return result.get("response", "")
        except Exception as e:
            raise Exception(f"Ollama bağlantı hatası: {str(e)}")


# Singleton instance
ollama_service = OllamaService()