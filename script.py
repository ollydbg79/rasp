import re
import json
import requests

def unpack_packer(js_code):
    # Mini desempaquetador P.A.C.K.E.R. simple
    packed = re.search(r"}\('(.*)', *(\d+), *(\d+), *'(.*)'\.split\('\|'\)", js_code)
    if not packed:
        return js_code
    payload, base, count, symtab = packed.groups()
    symtab = symtab.split('|')
    def lookup(match):
        word = match.group(0)
        try:
            index = int(word, int(base))
            return symtab[index] if index < len(symtab) else word
        except:
            return word
    return re.sub(r'\b\w+\b', lookup, payload)

def resolve_streamwish(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
            "Referer": url
        }

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        html = resp.text

        # Buscar iframe
        iframe = re.search(r'<iframe[^>]+src="(https?://[^"]+)"', html)
        if iframe:
            iframe_url = iframe.group(1)
            resp = requests.get(iframe_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                html = resp.text

        # Desempaquetar si está ofuscado
        packed = re.search(r'(eval\s*\(function\(p,a,c,k,e,.*?</script>)', html, re.DOTALL)
        if packed:
            html += unpack_packer(packed.group(1))

        # Buscar var links
        links_match = re.search(r"var\s+links\s*=\s*({[\s\S]+?});", html)
        if links_match:
            links_json = links_match.group(1).replace("'", '"')
            links = json.loads(links_json)
            if "hls2" in links:
                return links["hls2"]

        # Buscar en sources
        sources = re.search(r"sources\s*:\s*(\[[^\]]+\])", html)
        if sources:
            text = sources.group(1).replace("file:", "\"file\":")
            for source in json.loads(text):
                if source.get("file", "").endswith(".m3u8"):
                    return source["file"]

        # Fallback: .m3u8 directo
        m3u8 = re.search(r'"(https?://[^"]+\.m3u8[^"]*)"', html)
        if m3u8:
            return m3u8.group(1)

        return None
    except Exception as e:
        return None

# Ejemplo de uso
if __name__ == "__main__":
    url = "https://ghbrisk.com/e/2sdtbnxyoc5z"
    hls = resolve_streamwish(url)
    print(f"hls={hls if hls else 'None'}")




# streamwish vidhide filemoon
# https://filemoon.sx/e/ol14saommzli
# https://vidhidepro.com/v/4l680691a0oj
# https://streamwish.to/e/ku1j3ipw5w8k
