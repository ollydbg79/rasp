import re
import json
import cloudscraper


import sys
PY3 = False
if sys.version_info[0] >= 3: PY3 = True; unicode = str; unichr = chr; long = int

import re


def detect(source):
    global beginstr
    global endstr
    beginstr = ""
    endstr = ""
    begin_offset = -1
    """Detects whether source is P.A.C.K.E.R. coded."""
    if PY3 and isinstance(source, bytes):
        source = "".join(chr(x) for x in source)
    mystr = re.search(
    "eval[ ]*\\([ ]*function[ ]*\\([ ]*p[ ]*,[ ]*a[ ]*,[ ]*c["
    " ]*,[ ]*k[ ]*,[ ]*e[ ]*,[ ]*",
    source,
)
    if mystr:
        begin_offset = mystr.start()
        beginstr = source[:begin_offset]
    if begin_offset != -1:
        """ Find endstr"""
        source_end = source[begin_offset:]
        if source_end.split("')))", 1)[0] == source_end:
            try:
                endstr = source_end.split("}))", 1)[1]
            except IndexError:
                endstr = ""
        else:
            endstr = source_end.split("')))", 1)[1]
    return mystr is not None


def unpack(source):
    """Unpacks P.A.C.K.E.R. packed js code."""
    if PY3 and isinstance(source, bytes):
        source = "".join(chr(x) for x in source)
    payload, symtab, radix, count = _filterargs(source)
    if count != len(symtab):
        raise UnpackingError('Malformed p.a.c.k.e.r. symtab.')
    try:
        unbase = Unbaser(radix)
    except TypeError:
        raise UnpackingError('Unknown p.a.c.k.e.r. encoding.')
    
    def lookup(match):
        """Look up symbols in the synthetic symtab."""
        word = match.group(0)
        return symtab[unbase(word)] or word
    
    #payload = payload.replace("\\\\", "\\").replace("\\'", "'")
    if not PY3:
        source = re.sub(r"\b\w+\b", lookup, payload)
    else:
        source = re.sub(r"\b\w+\b", lookup, payload, flags=re.ASCII)
    return _replacestrings(source)


def _filterargs(source):
    """Juice from a source file the four args needed by decoder."""
    if PY3 and isinstance(source, bytes):
        source = "".join(chr(x) for x in source)
    juicers = [
        (r"}\('(.*)', *(\d+|\[\]), *(\d+), *'(.*)'\.split\('\|'\), *(\d+), *(.*)\)\)"),
        (r"}\('(.*)', *(\d+|\[\]), *(\d+), *'(.*)'\.split\('\|'\)"),
    ]
    for juicer in juicers:
        args = re.search(juicer, source, re.DOTALL)
        if args:
            a = args.groups()
            if a[1] == "[]":
                a = list(a)
                a[1] = 62
                a = tuple(a)
            try:
                return a[0], a[3].split('|'), int(a[1]), int(a[2])
            except ValueError:
                raise UnpackingError('Corrupted p.a.c.k.e.r. data.')
    # could not find a satisfying regex
    raise UnpackingError('Could not make sense of p.a.c.k.e.r data (unexpected code structure)')


def _replacestrings(source):
    global beginstr
    global endstr
    """Strip string lookup table (list) and replace values in source."""
    if PY3 and isinstance(source, bytes):
        source = "".join(chr(x) for x in source)
    match = re.search(r'var *(_\w+)\=\["(.*?)"\];', source, re.DOTALL)
    if match:
        varname, strings = match.groups()
        startpoint = len(match.group(0))
        lookup = strings.split('","')
        variable = '%s[%%d]' % varname
        for index, value in enumerate(lookup):
            source = source.replace(variable % index, '"%s"' % value)
        return source[startpoint:]
    try:
        if beginstr:
            pass
    except:
        beginstr = ''
        endstr = ''
    return beginstr + source + endstr


class Unbaser(object):
    """Functor for a given base. Will efficiently convert
    strings to natural numbers."""
    ALPHABET = {
        62: "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        95: (
            " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "[\\]^_abcdefghijklmnopqrstuvwxyz{|}~"
        ),
    }
    def __init__(self, base):
        self.base = base

        # fill elements 37...61, if necessary
        if 36 < base < 62:
            if not hasattr(self.ALPHABET, self.ALPHABET[62][:base]):
                self.ALPHABET[base] = self.ALPHABET[62][:base]
        # attrs = self.ALPHABET
        # print ', '.join("%s: %s" % item for item in attrs.items())   
        # If base can be handled by int() builtin, let it do it for us
        if 2 <= base <= 36:
            self.unbase = lambda string: int(string, base)
        else:
            # Build conversion dictionary cache
            try:
                self.dictionary = dict((cipher, index) for index, cipher in enumerate(self.ALPHABET[base]))
            except KeyError:
                raise TypeError('Unsupported base encoding.')
            self.unbase = self._dictunbaser
    
    def __call__(self, string):
        return self.unbase(string)
    
    def _dictunbaser(self, string):
        """Decodes a  value to an integer."""
        ret = 0
        for index, cipher in enumerate(string[::-1]):
            ret += (self.base ** index) * self.dictionary[cipher]
        return ret


class UnpackingError(Exception):
    """Badly packed source or general error. Argument is a
    meaningful description."""
    pass


def resolve_streamwish(url):
    try:
        scraper = cloudscraper.create_scraper()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0", "Referer": url}
        response = scraper.get(url, headers=headers, allow_redirects=True)
        if response.status_code != 200:
            return None
        html = response.text

        # Buscar iframe
        iframe_match = re.search(r'<iframe[^>]+src=\"(https?://[^\"]+)\"', html)
        if iframe_match:
            headers["Referer"] = url
            response = scraper.get(iframe_match.group(1), headers=headers)
            if response.status_code == 200:
                html = response.text

        # Desempaquetar JavaScript
        packed = re.search(r'eval\s*\(\s*function\s*\(p,a,c,k,e,[dr]\).*?</script>', html, re.DOTALL)
        if packed:
            html += unpack(packed.group(0))

        # Buscar var links
        links_match = re.search(r"var\s+links\s*=\s*({[\s\S]+?});", html, re.DOTALL)
        if links_match:
            links_json = links_match.group(1).replace("'", '"')
            links = json.loads(links_json)
            hls_url = links.get("hls2")
            if hls_url:
                return hls_url

        # Buscar sources
        sources_match = re.search(r"sources\s*:\s*(\[[^\]]+\])", html, re.DOTALL)
        if sources_match:
            sources_text = sources_match.group(1).replace("file:", "\"file\":")
            sources = json.loads(sources_text)
            for source in sources:
                hls_url = source.get("file")
                if hls_url and hls_url.endswith(".m3u8"):
                    return hls_url

        # Fallback: URL .m3u8
        m3u8_match = re.search(r"\"(https?://[^\"]+\.m3u8[^\"]*)\"", html)
        if m3u8_match:
            return m3u8_match.group(1)

        return None
    except:
        return None

url = "https://vidhidepro.com/v/n5s0g7mhty1m"
hls_url = resolve_streamwish(url)
print(f"hls={hls_url if hls_url else 'None'}")
