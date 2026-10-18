"""Families: each browser sees only its own children; a code opens the family elsewhere."""

from fastapi.testclient import TestClient

from athena import family


def client():
    import athena.api as api

    return TestClient(api.app)


def test_each_browser_gets_its_own_children():
    a, b = client(), client()
    la = a.get("/api/learners").json()
    lb = b.get("/api/learners").json()
    assert {x["name"]["en"] for x in la} == {"Sita", "Ram"}  # own copies of the demo children
    assert all(x["used_today"] == 0 and not any(x["recent_accuracy"].values()) for x in la)  # fresh history
    assert not {x["id"] for x in la} & {x["id"] for x in lb}  # never the same records
    other = lb[0]["id"]
    assert a.get(f"/api/learners/{other}").status_code == 404
    assert a.get(f"/api/learners/{other}/dashboard").status_code == 404
    assert a.get(f"/api/learners/{other}/stories").status_code == 404
    assert a.delete(f"/api/learners/{other}").status_code == 404
    assert b.get(f"/api/learners/{other}").status_code == 200  # still there for its family


def test_family_code_opens_the_same_family_and_forged_cookies_fail():
    a, b = client(), client()
    mine = {x["id"] for x in a.get("/api/learners").json()}
    code = a.get("/api/family").json()["code"]
    assert b.post("/api/family/join", json={"code": "0000-0000-0000-0000"}).status_code == 404
    assert b.post("/api/family/join", json={"code": code}).status_code == 200
    assert {x["id"] for x in b.get("/api/learners").json()} == mine
    c = client()
    fid = family.valid_code(code)
    c.cookies.set(family.COOKIE, f"{fid}.{'0' * 32}")  # right id, wrong signature
    assert not {x["id"] for x in c.get("/api/learners").json()} & mine


def test_sign_and_verify():
    fid = family.new_id()
    assert family.verify(family.sign(fid)) == fid
    assert family.verify(fid + ".deadbeef") is None and family.verify("../etc") is None
    assert family.valid_code(family.pretty(fid)) == fid
