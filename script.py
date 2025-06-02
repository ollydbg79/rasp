import requests
import cloudscraper
import re
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def resolve_streamwish(url):
    try:
        logger.info(f"Procesando URL: {url}")
        
        # Configurar cloudscraper con opciones avanzadas
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'linux',
                'mobile': False
            },
            delay=10
        )
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": url,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        
        logger.info("Enviando solicitud HTTP...")
        response = scraper.get(url, headers=headers, timeout=15)
        logger.info(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Error HTTP: {response.status_code}")
            if response.status_code == 403:
                logger.error("Cloudflare probablemente está bloqueando la solicitud")
            return None

        html = response.text
        logger.info(f"HTML recibido (primeros 500 caracteres): {html[:500]}...")

        # Buscar enlace HLS (múltiples patrones para mayor robustez)
        patterns = [
            r'"file":"(https?://[^"]+\.m3u8[^"]*)"',  # Patrón original
            r'"src":"(https?://[^"]+\.m3u8[^"]*)"',   # Alternativa
            r'(https?://[^\s"]+\.m3u8[^\s"]*)'        # Más genérico
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                hls_url = match.group(1)
                logger.info(f"Enlace HLS encontrado con patrón {pattern}: {hls_url}")
                return hls_url
        
        logger.error("No se encontró enlace HLS en el HTML")
        return None

    except Exception as e:
        logger.error(f"Excepción: {str(e)}")
        return None
