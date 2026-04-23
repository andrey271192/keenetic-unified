import hashlib, httpx

class KeeneticClient:
    def __init__(self, url, user, password):
        self.url = url.rstrip("/"); self.user = user; self.password = password

    async def check_connection(self):
        try:
            async with httpx.AsyncClient(timeout=10, verify=False) as c:
                r = await c.get(self.url + "/auth")
                if r.status_code == 200: return True
                if r.status_code == 401:
                    realm = r.headers.get("X-NDM-Realm", "")
                    challenge = r.headers.get("X-NDM-Challenge", "")
                    if realm and challenge:
                        md5 = hashlib.md5((self.user+":"+realm+":"+self.password).encode()).hexdigest()
                        sha = hashlib.sha256((challenge+md5).encode()).hexdigest()
                        r2 = await c.post(self.url+"/auth", json={"login":self.user,"password":sha})
                        return r2.status_code == 200
                return False
        except: return False
