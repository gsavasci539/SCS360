from collections import Counter
import re
from unicodedata import normalize


MOOD = {
    "happy": "happy", "mutlu": "happy", "çok neşeli & uyumlu": "happy", "mutlu & sakin": "happy",
    "calm": "calm", "sakin": "calm", "unsettled": "unsettled", "huzursuz": "unsettled",
    "tired": "tired", "yorgun": "tired", "biraz yorgun": "tired",
    "enerjik & hareketli": "other", "hassas & duygusal": "other",
}
SLEEP = {
    "slept_well": "slept", "iyi uyudu": "slept", "short": "short", "kısa uyku": "short",
    "no_sleep": "none", "uyku yok": "none", "uyumadı": "none",
}
MEAL = {
    "all": "full", "tam yedi": "full", "tümünü yedi": "full",
    "half": "partial", "yarım yedi": "partial", "yarısını yedi": "partial", "az yedi": "partial",
    "none": "none", "yemedi": "none",
}
MEAL_LABELS = {"kahvaltı", "öğle", "ara öğün"}
POSITIVE = {"mood": ("happy",), "sleep": ("slept", "short"), "meal": ("full",)}
ADVERSE = {"mood": ("tired", "unsettled"), "sleep": ("short", "none"), "meal": ("partial", "none")}
FOLLOW_UP = {
    "mood": "Bazı ruh hali kayıtlarında yorgunluk veya huzursuzluk işaretlendi.",
    "sleep": "Bazı uyku kayıtlarında kısa uyku veya uyumama işaretlendi.",
    "meal": "Bazı öğün kayıtlarında az yeme veya yememe işaretlendi.",
}


def observation_key(value: str | None) -> str:
    return " ".join(normalize("NFKC", value or "").casefold().replace("\u0307", "").split())


def observations(report):
    mood = MOOD.get(observation_key(report.mood))
    sleep_key = observation_key(report.sleep_status)
    sleep = SLEEP.get(sleep_key)
    if minutes := re.fullmatch(r"([0-9]{1,3}) dk", sleep_key):
        sleep = "slept" if int(minutes[1]) > 0 else "none"

    meals = []
    for part in observation_key(report.meal_status).split("/"):
        label, delimiter, value = part.partition(":")
        if delimiter and label.strip() not in MEAL_LABELS:
            continue
        if meal := MEAL.get((value if delimiter else label).strip()):
            meals.append(meal)
    return {"mood": [mood] if mood else [], "sleep": [sleep] if sleep else [], "meal": meals}


def count(counter, choices):
    return sum(counter[choice] for choice in choices)


def rate(counter, choices):
    total = counter.total()
    return round(100 * count(counter, choices) / total, 1) if total else None


def summarize_daily_reports(rows):
    totals = {domain: Counter() for domain in POSITIVE}
    students = {}
    for report, first, last in rows:
        student = students.get(report.student_id)
        if student is None:
            student = {"student_name": f"{first} {last}", "total_reports": 0,
                "observations": {domain: Counter() for domain in POSITIVE}}
            students[report.student_id] = student
        student["total_reports"] += 1
        for domain, entries in observations(report).items():
            totals[domain].update(entries)
            student["observations"][domain].update(entries)

    follow_up = []
    for student_id, student in students.items():
        counters = student["observations"]
        adverse_rates = [value for domain, options in ADVERSE.items() if (value := rate(counters[domain], options)) is not None]
        if not adverse_rates:
            continue
        adverse_rate = sum(adverse_rates) / len(adverse_rates)
        if adverse_rate > 30:
            follow_up.append({"student_id": str(student_id), "student_name": student["student_name"],
                "total_reports": student["total_reports"],
                **{f"poor_{domain}": count(counters[domain], options) for domain, options in ADVERSE.items()},
                "wellness_score": round(100 - adverse_rate, 1), "risk_level": "yüksek" if adverse_rate > 50 else "orta"})
    follow_up.sort(key=lambda row: (row["wellness_score"], row["student_id"]))

    recommendations = [FOLLOW_UP[domain] for domain, options in ADVERSE.items() if count(totals[domain], options)]
    if not rows:
        recommendations = ["Gösterilebilecek günlük karne bulunamadı."]
    elif not any(totals.values()):
        recommendations = ["Özetlenecek kayıtlı gözlem bulunamadı."]

    return {"ai_model": "Daily Reports Analytics v1.1", "report_stats": {
        "total": len(rows), "mood_happy": totals["mood"]["happy"], "mood_tired": totals["mood"]["tired"],
        **{f"{domain}_observations": counter.total() for domain, counter in totals.items()},
        **{f"{domain}_rate": rate(totals[domain], positive) for domain, positive in POSITIVE.items()},
    }, "students_needing_attention": follow_up[:10], "recommendations": recommendations}
