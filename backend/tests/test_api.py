from tests.conftest import NOTES


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "ai": "demo"}


def test_lesson_requires_teacher_token(client, classroom):
    r = client.post(f"/api/classrooms/{classroom['code']}/lesson", data={"notes": NOTES})
    assert r.status_code == 403


def test_full_lesson_and_rag_flow(client, classroom):
    code, token = classroom["code"], classroom["teacher_token"]
    r = client.post(f"/api/classrooms/{code}/lesson", data={"notes": NOTES}, headers={"x-teacher-token": token})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chunks_indexed"] >= 1 and len(body["lesson"]["scenes"]) >= 2

    assert client.get(f"/api/classrooms/{code}").json()["has_lesson"] is True
    assert client.get(f"/api/classrooms/{code.lower()}/lesson").status_code == 200

    r = client.post(f"/api/classrooms/{code}/ask", json={"student": "Riya", "question": "Where do plants get carbon dioxide?"})
    assert r.status_code == 200
    out = r.json()
    assert out["sources"] and "stomata" in out["sources"][0]["text"]

    report = client.get(f"/api/classrooms/{code}/report", headers={"x-teacher-token": token}).json()
    assert report["doubts"][0]["student"] == "Riya"


def test_text_file_upload(client, classroom):
    r = client.post(f"/api/classrooms/{classroom['code']}/lesson",
                    files={"file": ("notes.txt", NOTES.encode(), "text/plain")},
                    headers={"x-teacher-token": classroom["teacher_token"]})
    assert r.status_code == 200, r.text


def test_photo_upload_needs_ai_key(client, classroom):
    r = client.post(f"/api/classrooms/{classroom['code']}/lesson",
                    files={"file": ("notes.jpg", b"\xff\xd8fake", "image/jpeg")},
                    headers={"x-teacher-token": classroom["teacher_token"]})
    assert r.status_code == 422 and "GEMINI_API_KEY" in r.json()["detail"]


def test_unknown_class_404(client):
    assert client.get("/api/classrooms/ZZZZZZ").status_code == 404
