from tests.conftest import NOTES


def test_teacher_moves_scene_and_sees_live_answers(client, classroom):
    code, token = classroom["code"], classroom["teacher_token"]
    client.post(f"/api/classrooms/{code}/lesson", data={"notes": NOTES}, headers={"x-teacher-token": token})

    with client.websocket_connect(f"/ws/{code}?role=teacher&token={token}") as teacher, \
            client.websocket_connect(f"/ws/{code}?role=student&name=Aman") as student:
        assert teacher.receive_json() == {"type": "scene", "index": 0}
        assert teacher.receive_json() == {"type": "presence", "students": []}
        assert teacher.receive_json() == {"type": "presence", "students": ["Aman"]}
        assert student.receive_json() == {"type": "scene", "index": 0}

        teacher.send_json({"type": "goto", "index": 2})
        assert teacher.receive_json() == {"type": "scene", "index": 2}
        assert student.receive_json() == {"type": "scene", "index": 2}

        student.send_json({"type": "answer", "scene": 2, "question": 0, "choice": 1})
        assert student.receive_json() == {"type": "answer_result", "scene": 2, "question": 0, "correct": True}
        stats = teacher.receive_json()
        assert stats["type"] == "stats" and stats["counts"] == [0, 1, 0, 0]


def test_wrong_teacher_token_is_rejected(client, classroom):
    import pytest
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/{classroom['code']}?role=teacher&token=nope") as ws:
            ws.receive_json()
