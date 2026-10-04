import os, time, hashlib
from collections import deque
from urllib.parse import urljoin, urldefrag, urlparse
import requests
from bs4 import BeautifulSoup

MEILI_URL=os.getenv("MEILI_URL","http://meilisearch:7700")
MEILI_KEY=os.getenv("MEILI_KEY","")
SEEDS=[x.strip() for x in os.getenv("SEEDS","https://example.com/").split(",") if x.strip()]
MAX_PAGES=int(os.getenv("MAX_PAGES","200"))
MAX_DEPTH=int(os.getenv("MAX_DEPTH","3"))
DELAY=float(os.getenv("CRAWL_DELAY","0.5"))
MAX_CHARS=int(os.getenv("MAX_DOC_CHARS","120000"))

s=requests.Session()
s.headers.update({"User-Agent":"MyLocalSearchBot/1.0 (local educational crawler)"})
headers={"Authorization":f"Bearer {MEILI_KEY}","Content-Type":"application/json"}

def same_site(url, hosts):
    p=urlparse(url)
    return p.scheme in ("http","https") and p.hostname in hosts

def text_of(soup):
    for x in soup(["script","style","noscript","svg","canvas"]): x.decompose()
    return " ".join(soup.get_text(" ",strip=True).split())

def wait_meili():
    for _ in range(60):
        try:
            if s.get(MEILI_URL+"/health",timeout=2).ok: return True
        except Exception: pass
        time.sleep(2)
    return False

def main():
    if not wait_meili():
        raise SystemExit("Meilisearch did not become ready")

    # Create the index only if it does not already exist.
    try:
        existing = s.get(MEILI_URL+"/indexes/pages",headers=headers,timeout=10)
        if existing.status_code == 404:
            s.post(MEILI_URL+"/indexes",json={"uid":"pages","primaryKey":"id"},headers=headers,timeout=10).raise_for_status()
            time.sleep(1)
    except Exception:
        pass

    # Configure fields. These requests are safe to repeat.
    settings = [
        ("/indexes/pages/settings/searchable-attributes",["title","content","url"]),
        ("/indexes/pages/settings/displayed-attributes",["title","url","content","description","image"]),
    ]
    for endpoint, payload in settings:
        try:
            s.put(MEILI_URL+endpoint,json=payload,headers=headers,timeout=10)
        except Exception:
            pass

    hosts={urlparse(x).hostname for x in SEEDS}
    q=deque((x,0) for x in SEEDS)
    seen=set(); batch=[]

    while q and len(seen)<MAX_PAGES:
        url,depth=q.popleft()
        url=urldefrag(url)[0]
        if url in seen or depth>MAX_DEPTH or not same_site(url,hosts): continue
        seen.add(url)
        try:
            r=s.get(url,timeout=15,allow_redirects=True)
            if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): continue
            final=urldefrag(r.url)[0]
            soup=BeautifulSoup(r.text,"html.parser")
            title=soup.title.get_text(" ",strip=True) if soup.title else final
            desc=""
            meta=soup.find("meta",attrs={"name":"description"})
            if meta: desc=meta.get("content","").strip()
            image=""
            og=soup.find("meta",attrs={"property":"og:image"})
            if og: image=urljoin(final,og.get("content",""))
            else:
                img=soup.find("img",src=True)
                if img: image=urljoin(final,img.get("src",""))
            content=text_of(soup)
            if content:
                docid=hashlib.sha256(final.encode()).hexdigest()
                batch.append({"id":docid,"title":title[:500],"url":final,
                              "content":content[:MAX_CHARS],"description":desc[:1000],"image":image[:2000]})
            if depth<MAX_DEPTH:
                for a in soup.find_all("a",href=True):
                    nxt=urldefrag(urljoin(final,a["href"]))[0]
                    if same_site(nxt,hosts) and nxt not in seen: q.append((nxt,depth+1))
            print(f"[{len(seen)}/{MAX_PAGES}] {final}")
            if len(batch)>=20:
                s.post(MEILI_URL+"/indexes/pages/documents",json=batch,headers=headers,timeout=30).raise_for_status()
                batch=[]
            time.sleep(DELAY)
        except Exception as e:
            print("ERROR",url,repr(e))

    if batch:
        s.post(MEILI_URL+"/indexes/pages/documents",json=batch,headers=headers,timeout=30).raise_for_status()
    print("CRAWL COMPLETE:",len(seen),"pages visited")

if __name__=="__main__": main()
