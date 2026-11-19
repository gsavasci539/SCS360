from datetime import date

from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_daily_report_roundtrip_and_branch_filter(materials_client):  # noqa: F811
    client, _, data = materials_client
    child = data["children"][0]
    path = "/api/daily-reports"
    authorization = headers(data["teacher"])
    today = date(2026, 11, 19).isoformat()
    draft = {"student_id": str(child.id), "class_id": str(child.class_id), "date": today,
        "meal_breakfast": "Tümünü Yedi", "meal_lunch": "Yarısını Yedi", "meal_snack": "Az Yedi",
        "sleep_status": "30 dk", "mood": "Sakin", "activities": ["Çizim"], "teacher_notes": "Kayıtlı gözlem"}
    assert (await client.post(path, headers=headers(data["user"]), json=draft)).status_code == 403
    response = await client.post(path, headers=authorization, json=draft)
    assert response.status_code == 200, response.text
    row = response.json()["data"]
    assert row["meal_status"] == "Kahvaltı: Tümünü Yedi / Öğle: Yarısını Yedi / Ara öğün: Az Yedi"
    assert row["recorded_by"] == str(data["teacher"].id)
    assert row["sleep_status"] == "30 dk" and row["activities"] == ["Çizim"]
    assert (await client.get(f'{path}/{row["id"]}', headers=authorization)).json()["data"] == row
    params = {"student_id": str(child.id), "date": today, "branch_id": str(data["branch"].id)}
    assert (await client.get(path, headers=authorization, params=params)).json()["data"]["items"] == [row]
    assert (await client.get(path, headers=authorization, params={**params,
        "branch_id": str(data["other_branch"].id)})).json()["data"]["items"] == []
    assert (await client.post(path, headers=authorization, json=draft)).status_code == 409
