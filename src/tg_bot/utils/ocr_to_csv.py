import json

from .ycloud_client import get_ycloud_sdk

prompt = """
Ты — парсер медбланков (RU). На входе JSON с ключом "text_lines": [{"text": str, "confidence": float, "bbox":[x0,y0,x1,y1]}].

Задача: извлечь таблицу анализов и вернуть СТРОГО CSV-СТРОКИ (UTF-8) формата:
date,analysis,result,status
— без какого-либо заголовка и префиксов/пояснений.

Правила:
1) Нормализуй порядок:
   - Сгруппируй элементы в строки по близости по Y (допуск ≈ 0.5*медианной высоты, но ≥3 px).
   - Внутри строки сортируй по X слева→направо.
   - Вертикально смежные фрагменты одного заголовка (большое X-перекрытие, малый Y-зазор) считаются последовательными, напр. «Референсные» + «значения».
2) Определи колонки по заголовкам/синонимам:
   Исследование|Показатель|Наименование; Результат; Единицы|Ед.; Референсные значения|Норма|Диапазон; Комментарий|Примечание.
3) Построй строки анализов, сопоставив: исследование — результат — (единицы) — (референс) — (комментарий).
4) Дата (одна для всех строк бланка), приоритет: «Дата взятия образца» > «Дата печати результата» > «Дата поступления образца». Формат YYYY-MM-DD (только дата).
5) Нормализация текста:
   - Удали HTML/теги (<br>, <math>...), лишние пробелы.
   - Десятичные запятые заменяй на точки.
6) status ∈ {ok, attention, abnormal, invalid}:
   - Если есть числовой референс (напр. "3.0 - 11.0") и числовой result — сравни: внутри/на границе → ok, вне → abnormal.
   - Ключевые слова: «повышен/понижен/вне нормы/не соответствует» → abnormal; «см. примечание/следует контролировать/пограничное» → attention; «возможна лабораторная ошибка/может быть неверным» → invalid.
   - Иначе при наличии результата → ok.
7) Вывод:
   - Верни ТОЛЬКО строки CSV без заголовка; одна строка = один анализ.
   - Поля с запятыми/кавычками бери в двойные кавычки, внутренние двойные кавычки удваивай.
   - Ничего не выдумывай; если пара «анализ–результат» не распознана — пропусти.
   - Дату выводи всегда в формате yyyy-mm-dd

Входной JSON:
{ocr_json_here}
"""

def ocr_results_to_csv(ocr_results: list) -> str | None:
    sdk = get_ycloud_sdk()
    model = sdk.models.completions("yandexgpt").configure(temperature=0.5)

    ocr_data = []
    for page in ocr_results:
        page_data = {
            "text_lines": [
                {
                    "text": line.text,
                    "bbox": line.bbox
                } for line in page.text_lines
            ]
        }
        ocr_data.append(page_data)

    # ocr_data может быть dict/list — превращаем в строку
    ocr_data_str = (
        ocr_data if isinstance(ocr_data, str)
        else json.dumps(ocr_data, ensure_ascii=False)
    )

    payload = f"{prompt}\n{ocr_data_str}"

    result = model.run(payload)

    text = result.alternatives[0].text

    if text.startswith('```'):
        text = text[3:]
    if text.startswith('csv'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.replace(', ', ' ')
    if 'JSON' in text or 'Я не могу' in text:
        return None

    try:
        return text
    except Exception as e:
        print("Full result object:", result)
        raise

