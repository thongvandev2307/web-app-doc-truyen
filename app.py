from html import escape
from flask import Flask, Response, request
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse, urljoin

try:
    from curl_cffi import requests as curl_requests
    _USE_CURL_CFFI = True
except ImportError:
    curl_requests = None
    _USE_CURL_CFFI = False

app = Flask(__name__)

_CHROME_IMPERSONATE = 'chrome124'
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
)


def http_get(url: str, headers: dict[str, str], *, stream: bool = False, timeout: int = 60):
    if _USE_CURL_CFFI and curl_requests is not None:
        return curl_requests.get(
            url,
            headers=headers,
            impersonate=_CHROME_IMPERSONATE,
            timeout=timeout,
            stream=stream,
        )
    return requests.get(url, headers=headers, timeout=timeout, stream=stream)

# Thử lần lượt; nhiều theme Madara / WordPress / reader khác nhau
MANGA_IMG_SELECTORS = (
    '.reading-content img',
    '.reading-content-box img',
    '#reader img',
    '.chapter-content img',
    '.entry-content img',
    '.c-page-comic img',
    'div.reading img',
    'article img',
)


def origin_from_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f'{parsed.scheme}://{parsed.netloc}/'
    return ''


def request_headers_for(
    resource_url: str,
    page_url: str | None = None,
    *,
    for_image: bool = False,
) -> dict[str, str]:
    if page_url:
        referer = page_url
    else:
        referer = origin_from_url(resource_url)
    if not referer:
        referer = 'https://example.com/'
    parsed = urlparse(resource_url)
    site = (
        'cross-site'
        if parsed.netloc and referer and parsed.netloc not in referer
        else 'same-origin'
    )
    headers: dict[str, str] = {
        'User-Agent': USER_AGENT,
        'Referer': referer,
        'Accept-Language': 'en-US,en;q=0.9,ko;q=0.85,vi;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
    }
    if for_image:
        headers['Accept'] = (
            'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
        )
        headers['Sec-Fetch-Dest'] = 'image'
        headers['Sec-Fetch-Mode'] = 'no-cors'
        headers['Sec-Fetch-Site'] = site
    else:
        headers['Accept'] = (
            'text/html,application/xhtml+xml,application/xml;q=0.9,'
            'image/avif,image/webp,*/*;q=0.8'
        )
        headers['Upgrade-Insecure-Requests'] = '1'
        headers['Sec-Fetch-Dest'] = 'document'
        headers['Sec-Fetch-Mode'] = 'navigate'
        headers['Sec-Fetch-Site'] = 'none'
        headers['Sec-Fetch-User'] = '?1'
    return headers


def collect_manga_image_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for selector in MANGA_IMG_SELECTORS:
        for img in soup.select(selector):
            raw = img.get('data-src') or img.get('data-lazy-src') or img.get('src')
            if not raw or raw.startswith('data:'):
                continue
            if raw.startswith('//'):
                raw = 'https:' + raw
            elif not raw.startswith(('http://', 'https://')):
                raw = urljoin(base_url, raw)
            if raw in seen:
                continue
            seen.add(raw)
            urls.append(raw)
    return urls


@app.route('/')
def read_manga():
    target_url = request.args.get(
        'url',
        "https://roadsteam.net/manga/stage-behind/chap-30/"
    )
    
    try:
        page_headers = request_headers_for(target_url, for_image=False)
        response = http_get(target_url, page_headers, stream=False, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        image_urls = collect_manga_image_urls(soup, target_url)
        
        html_content = """
        <html>
            <head>
                <meta charset='utf-8'>
                <meta name='viewport' content='width=device-width, initial-scale=1'>
                <title>Manga Proxy Reader</title>
                <style>
                    :root {
                        --bg: #101218;
                        --card: #1b2030;
                        --card-soft: #242b40;
                        --text: #e8ecf5;
                        --muted: #a9b3c8;
                        --accent: #66b3ff;
                        --accent-2: #4f8dff;
                    }
                    * { box-sizing: border-box; }
                    body {
                        margin: 0;
                        background: radial-gradient(circle at top, #172032, var(--bg));
                        color: var(--text);
                        font-family: Segoe UI, Roboto, Arial, sans-serif;
                    }
                    .container {
                        max-width: 960px;
                        margin: 0 auto;
                        padding: 24px 16px 40px;
                    }
                    .panel {
                        background: linear-gradient(180deg, var(--card), var(--card-soft));
                        border: 1px solid #2f3850;
                        border-radius: 16px;
                        padding: 16px;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
                    }
                    h1 {
                        margin: 0 0 8px;
                        font-size: 24px;
                    }
                    .subtitle {
                        margin: 0 0 14px;
                        color: var(--muted);
                    }
                    form {
                        display: flex;
                        gap: 10px;
                        flex-wrap: wrap;
                    }
                    input[type='url'] {
                        flex: 1;
                        min-width: 280px;
                        padding: 12px 14px;
                        border-radius: 12px;
                        border: 1px solid #3a4562;
                        background: #121826;
                        color: var(--text);
                        outline: none;
                    }
                    input[type='url']:focus {
                        border-color: var(--accent);
                        box-shadow: 0 0 0 2px rgba(102, 179, 255, 0.2);
                    }
                    button {
                        border: 0;
                        border-radius: 12px;
                        padding: 12px 18px;
                        color: white;
                        font-weight: 600;
                        background: linear-gradient(135deg, var(--accent), var(--accent-2));
                        cursor: pointer;
                    }
                    .stats {
                        margin-top: 10px;
                        color: var(--muted);
                        font-size: 14px;
                    }
                    .images {
                        margin-top: 18px;
                    }
                    .page {
                        margin: 0 auto 10px;
                        background: #0f1422;
                        border-radius: 10px;
                        overflow: hidden;
                        border: 1px solid #283048;
                    }
                    .page img {
                        width: 100%;
                        max-width: 860px;
                        display: block;
                        margin: 0 auto;
                    }
                </style>
            </head>
            <body>
                <div class='container'>
                    <div class='panel'>
                        <h1>Server REM~TVT - Đọc truyện không bị chặn</h1>
                        <p class='subtitle'>Dán URL trang chương bất kỳ (Madara / WordPress reader tương tự). Ảnh tải qua proxy server.</p>
                        <form method='get' action='/'>
                            <input
                                type='url'
                                name='url'
                                value='"""
        html_content += escape(target_url, quote=True)
        html_content += """'
                                placeholder='https://ten-site.com/manga/.../chap-1/'
                                required
                            >
                            <button type='submit'>Tải chương</button>
                        </form>
                        <div class='stats'>Số ảnh tìm thấy: """
        html_content += str(len(image_urls))
        html_content += """</div>
                    </div>
                    <div class='images'>
        """
        
        encoded_ref = quote(target_url, safe='')
        for img_url in image_urls:
            encoded_url = quote(img_url, safe=':/?&=%')
            proxy_img_url = f"/image?url={encoded_url}&ref={encoded_ref}"
            html_content += f"<div class='page'><img src='{proxy_img_url}' loading='lazy'></div>"
                
        html_content += """
                    </div>
                </div>
            </body>
        </html>
        """
        return html_content
        
    except Exception as e:
        return f"""
        <div style='font-family:Segoe UI,Arial,sans-serif;padding:20px;background:#130f15;color:#ffd7d7'>
            <h2 style='margin-top:0;color:#ff8f8f'>Lỗi khi tải truyện</h2>
            <div>{e}</div>
            <p><a style='color:#8fc8ff' href='/'>Quay lại trang chính</a></p>
        </div>
        """

# Bước cực kỳ quan trọng: Server của bạn trực tiếp stream (truyền) ảnh cho người bên Hàn
@app.route('/image')
def get_image():
    img_url = request.args.get('url')
    if not img_url:
        return "Thiếu URL ảnh", 400
    page_ref = request.args.get('ref')
    img_headers = request_headers_for(img_url, page_url=page_ref, for_image=True)
    try:
        req = http_get(img_url, img_headers, stream=True, timeout=60)
        req.raise_for_status()
    except Exception as err:
        return f"Lỗi tải ảnh: {err}", 502
    return Response(
        req.iter_content(chunk_size=1024),
        content_type=req.headers.get('Content-Type', 'image/jpeg')
    )

if __name__ == '__main__':
    # Chạy server ở cổng 5000
    app.run(port=5000)
