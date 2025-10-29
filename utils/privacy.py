import hashlib

def hash_ip(ip: str, salt: str) -> str:
    if not ip:
        return ""
    payload = (salt + ip).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
