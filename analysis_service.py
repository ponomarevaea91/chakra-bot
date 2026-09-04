from data import CHAKRAS

SPHERE_RULES = {
    "health": {1: 0.22, 2: 0.16, 3: 0.18, 4: 0.14, 5: 0.08, 6: 0.10, 7: 0.12},
    "relationships": {1: 0.12, 2: 0.22, 3: 0.12, 4: 0.28, 5: 0.16, 6: 0.05, 7: 0.05},
    "money": {1: 0.20, 2: 0.14, 3: 0.25, 4: 0.08, 5: 0.20, 6: 0.08, 7: 0.05},
}

SPHERE_TITLES = {
    "health": "❤️ Здоровье и ресурс",
    "relationships": "🤝 Отношения",
    "money": "💰 Деньги и реализация",
}

SPHERE_ADVICE = {
    "health": "Поддерживайте базовый режим, отдых и бережное отношение к телу. Этот блок — инструмент саморефлексии и не заменяет медицинскую диагностику.",
    "relationships": "Обратите внимание на взаимность, границы и способность прямо говорить о своих чувствах и потребностях.",
    "money": "Посмотрите, где можно добавить структуру, ясность ценности, спокойное называние цены и регулярные действия.",
}

def level(score):
    if score < 2.5:
        return "🔴 зона внимания"
    if score < 3.8:
        return "🟡 зона баланса"
    return "🟢 ресурсная зона"

def analyze_spheres(scores):
    result = {}
    for sphere, weights in SPHERE_RULES.items():
        value = sum(float(scores.get(chakra, 0)) * weight for chakra, weight in weights.items())
        weakest = sorted(weights, key=lambda c: scores.get(c, 0))[:2]
        strongest = sorted(weights, key=lambda c: scores.get(c, 0), reverse=True)[:2]
        result[sphere] = {
            "score": round(value, 2),
            "level": level(value),
            "weakest": weakest,
            "strongest": strongest,
        }
    return result

def sphere_text(scores):
    analyses = analyze_spheres(scores)
    lines = ["📊 <b>Анализ трёх сфер</b>"]
    for sphere in ("health", "relationships", "money"):
        item = analyses[sphere]
        weak = ", ".join(CHAKRAS[c]["name"] for c in item["weakest"])
        strong = ", ".join(CHAKRAS[c]["name"] for c in item["strongest"])
        lines += [
            f"\n<b>{SPHERE_TITLES[sphere]}</b>: {item['score']}/5 — {item['level']}",
            f"Опора: {strong}.",
            f"Внимание: {weak}.",
            SPHERE_ADVICE[sphere],
        ]
    lines.append("\n<i>Это саморефлексивный анализ, а не медицинская, психологическая или финансовая диагностика.</i>")
    return "\n".join(lines)
