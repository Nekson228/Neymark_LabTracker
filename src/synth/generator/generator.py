from typing import Optional, Any
import random

from datetime import timedelta

from dataclasses import dataclass, asdict
from faker import Faker

fake = Faker("ru_RU")

@dataclass
class AnalysisRow:
    name: str
    value: str
    unit: str
    reference: str
    comment: Optional[str] = ""

@dataclass
class ReportData:
    patient_name: str
    gender: str
    age: int
    date_taken: str
    date_received: str
    doctor_date: str
    print_date: str
    clinic_name: str
    clinic_city: str
    analyses: list[AnalysisRow]
    general_comment: Optional[str]
    executor_name: str
    executor_position: str
    site: str
    main_font: str
    row_separator: bool
    font_size: int

    def to_dict(self) -> dict[str, Any]:
        """Convert dataclass (with nested rows) to plain dict for templating."""
        data = asdict(self)
        data["analyses"] = [asdict(a) for a in self.analyses]
        return data
    
    def get_metadata(self) -> dict[str, Any]:
        """Get metadata for PDF properties."""
        return {
            "font": self.main_font,
            "font_size": self.font_size,
            "row_separator": self.row_separator,
        }


ANALYTES = [
    ("Глюкоза", "ммоль/л", (4.1, 6.0)),
    ("Креатинин", "мкмоль/л", (64, 104)),
    ("ТТГ", "мЕд/л", (0.4, 4.0)),
    ("Холестерин общий", "ммоль/л", (3.0, 5.2)),
    ("Холестерин ЛПНП", "ммоль/л", (1.8, 3.3)),
    ("Холестерин ЛПВП", "ммоль/л", (0.9, 2.0)),
    ("Триглицериды", "ммоль/л", (0.5, 1.7)),
    ("Витамин D", "нг/мл", (20, 100)),
    ("Ферритин", "нг/мл", (30, 400)),
    ("Гемоглобин", "г/дл", (13.0, 17.5)),
    ("Эритроциты", "10\\^{}12/л", (4.0, 5.5)),
    ("Лейкоциты", "10\\^{}9/л", (4.0, 9.0)),
    ("Нейтрофилы", "\\%", (48, 78)),
    ("Лимфоциты", "\\%", (19, 37)),
    ("Моноциты", "\\%", (3, 11)),
    ("Эозинофилы", "\\%", (0.5, 5.0)),
    ("Базофилы", "\\%", (0, 1.0)),
    ("Мочевина", "ммоль/л", (2.5, 8.3)),
    ("Кальций общий", "ммоль/л", (2.2, 2.6)),
    ("Магний", "ммоль/л", (0.7, 1.1)),
    ("С-реактивный белок", "мг/л", (0, 5)),
    ("Альбумин", "г/л", (35, 50)),
    ("Билирубин общий", "мкмоль/л", (3.4, 17.1)),
]

COMMENTS = [
    "в норме",
    "повышен",
    "ниже нормы",
    "чуть выше нормы",
    "см. примечание",
    "рекомендуется повторное исследование",
    "",
    "значение временно повышено, повторно через 2 недели",
    "значение может быть искажено после приема пищи",
    "рекомендуется консультация профильного специалиста",
    "следует контролировать динамику показателя в течение месяца",
    "обратите внимание на возможное влияние лекарственных средств",
    "результат может быть неверным при лабораторной ошибке",
]

FONTS = [
    "DejaVu Sans",
    "Liberation Sans",
    "Arial",
    "PT Sans",
    "Times New Roman",
]

FONT_SIZES = [10, 11, 12, 13]

def generate_analysis_rows(n: int) -> list[AnalysisRow]:
    """Generate n random analyte rows."""
    choices = random.sample(ANALYTES, k=min(n, len(ANALYTES)))
    rows: list[AnalysisRow] = []

    for name, unit, (low, high) in choices:
        value = round(random.uniform(low * 0.8, high * 1.2), 2)
        ref = f"{low:.1f}–{high:.1f}"
        comment = random.choice(COMMENTS) if random.random() < 0.6 else ""
        rows.append(AnalysisRow(name, str(value), unit, ref, comment))

    return rows


def generate_report() -> ReportData:
    """Generate one full report record."""
    gender = random.choice(["Муж", "Жен"])
    name = fake.name_male() if gender == "Муж" else fake.name_female()
    num_rows = fake.random_int(min=5, max=10)

    base_date = fake.date_time_between(start_date='-30d', end_date='now')
    taken = base_date - timedelta(days=fake.random_int(min=0, max=5))
    received = taken + timedelta(hours=fake.random_int(min=2, max=8))
    doctor = received + timedelta(hours=fake.random_int(min=10, max=20))

    return ReportData(
        patient_name=name.upper(),
        gender=gender,
        age=fake.random_int(min=18, max=80),
        date_taken=taken.strftime("%d.%m.%Y %H:%M"),
        date_received=received.strftime("%d.%m.%Y %H:%M"),
        doctor_date=doctor.strftime("%d.%m.%Y %H:%M"),
        print_date=(doctor + timedelta(hours=2)).strftime("%d.%m.%Y"),
        clinic_name=fake.company(),
        clinic_city=fake.city_name(),
        analyses=generate_analysis_rows(num_rows),
        general_comment=random.choice([
            "", 
            "Результаты в пределах нормы.",
            "Рекомендовано повторное обследование через 6 месяцев.",
        ]),
        executor_name=fake.name_female(),
        executor_position="врач клинической лабораторной диагностики",
        site="www.neymark-labtracker.com",
        main_font=random.choice(FONTS), 
        row_separator=fake.boolean(chance_of_getting_true=70),
        font_size=random.choice(FONT_SIZES),
    )