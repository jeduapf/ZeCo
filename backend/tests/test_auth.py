import requests

BASE = "http://localhost:8000"

def test_login_and_admin():
    r = requests.post(f"{BASE}/api/v1/auth/token", data={"username":"admin","password":"admin"})
    assert r.status_code == 200
    token = r.json().get("access_token")
    assert token
    headers = {"Authorization": f"Bearer {token}"}
    ra = requests.get(f"{BASE}/api/v1/admin/only", headers=headers)
    assert ra.status_code == 200
    assert "admin access granted" in ra.json().get("msg", "")
