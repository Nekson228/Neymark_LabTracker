import json
import csv
import io
import os

from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field

import pandas as pd

from typing import List
from PIL import Image
from yandex_cloud_ml_sdk import YCloudML

from surya.foundation import FoundationPredictor
from surya.recognition import RecognitionPredictor
from surya.detection import DetectionPredictor

from src.tg_bot.utils.ocr_to_csv import ocr_results_to_csv

os.environ["RECOGNITION_BATCH_SIZE"]="256"
os.environ["FOUNDATION_MODEL_QUANTIZE"]="False"

from ..models.analysis_models import AnalysisScan, AnalysisResult, AnalysisHistory, AnalysesQuery
from ..utils.ycloud_client import get_ycloud_sdk

# Dummy in-memory storage
scans_db: List[AnalysisScan] = []
results_db: List[AnalysisResult] = []

sdk = YCloudML(
    folder_id="b1g08sdauols3um0k8qc",
    auth="y0__xCU55f0AhjB3RMg0Lrc2BTCzRuzRQUc4ah05BqajttLTaVqQQ",
)

def parse_surya_prediciton(prediction_list: list) -> list:
    '''
    парсит аутпут surya из api, возвращает спиосочек соответствующих    текстов, внутри картинки разделены с помощью <br>
    
    prediction_list - спиоск аутпутов surya (n картинок - n аутпутов)
    если в pdf несколько страниц, то всё равно в одном аутпутов
    '''
    
    text_annotation_list = []
    for pred in prediction_list:
        text_lines = pred.text_lines
        
        sorted_text_lines = sorted(text_lines, key=lambda text_line: (text_line.bbox[1], text_line.bbox[0]))
        text_annotation = ' '.join(text_line.text for text_line in sorted_text_lines)
        
        text_annotation_list.append(text_annotation)
    return text_annotation_list




class AnalysisService:
    foundation_predictor = FoundationPredictor()
    recognition_predictor = RecognitionPredictor(foundation_predictor)
    detection_predictor = DetectionPredictor()

    @staticmethod
    def analyse_by_prompt(user_id: int, user_prompt: str) -> AnalysisResult:
        df = pd.read_csv('analysis_results.csv', names=['user_id', 'date', 'analysis', 'result', 'status'])
        user_df = df[df["user_id"] == user_id]

        if user_df.empty:
            # Если нет текста для анализа, создаем специальный результат
            result = AnalysisResult(
                user_id=user_id,
                summary="Не найдено обработанных сканов для анализа. Пожалуйста, загрузите фото с помощью команды /scan.",
                generated_at=datetime.utcnow(),
            )
            # Не добавляем его в основную базу, так как это не реальный анализ
            return result
        
        previous_texts = user_df.to_string()

        prompt = (
            '''Ты — ассистент по истории меданализов (RU). Дано:
                1) CSV (UTF-8), строки формата: date,analysis,result,status (status ∈ {ok, attention, abnormal, invalid})
                2) Текстовый запрос пользователя.

                Требуется: понять запрос и дать краткую оценку состояния, опираясь ТОЛЬКО на CSV (внешние источники и домыслы запрещены). Диагнозы и рекомендации препаратов/витаминов — ЗАПРЕЩЕНЫ; при необходимости советуй обратиться к врачу.

                Правила:
                - Нормализуй сопоставление показателей (регистр+простые синонимы: «ЛПВП»~«HDL», «глюкоза»~«glucose»), в ответе сохраняй оригинальные названия из CSV.
                - Если есть дата/период в запросе — фильтруй по date (YYYY-MM-DD); иначе бери последние значения по каждому показателю.
                - Поддерживаемые намерения: последние значения; тренд (покажи 3–6 последних точек, опиши «рост/падение/стабильно» с допуском ~2–3%); что выходило из нормы; даты сдачи; сводка за дату/период; сравнение показателей.
                - Интерпретация status: ok — «в норме»; attention — «в норме, но есть пометки/наблюдение»; abnormal — «есть отклонения»; invalid — «результат недостоверен/сомнителен».
                - Тон нейтральный. Если просят «что принимать/лечить» — сообщи, что не можешь рекомендовать лекарства, и предложи обратиться к врачу.
                - Формат ответа: 1–2 предложения с выводом; при необходимости — краткий маркированный список «дата — анализ — результат — статус»; финальная строка: «Это не медицинский диагноз. Для интерпретации обратитесь к врачу.»
                - Никогда не используй блоки кода/ограждения '''+ "( / ''' /" + '""") в ответе.' +

                f"""Вход:
                CSV: {previous_texts}
                Запрос: {user_prompt}"""
        )

        response = AnalysisService._summarize_with_yandexgpt(prompt)

        result = AnalysisResult(
            user_id=user_id,
            summary=response,
            generated_at=datetime.utcnow(),
        )
        
        return result

    @staticmethod
    def save_scan_to_csv(raw_csv_text: str):
        """
        Парсит строку с CSV-данными и добавляет их в файл analysis_results.csv.
        Корректно обрабатывает заголовок.
        """
        output_filename = 'analysis_results.csv'
        print("Saving\n", raw_csv_text)
        
        lines = raw_csv_text.strip().split('\n')

        csv_content = "\n".join(lines)

        string_io = io.StringIO(csv_content)
        reader = csv.reader(string_io)
        data_rows = list(reader)

        file_exists = os.path.exists(output_filename)

        with open(output_filename, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Затем дописываем новые строки с данными
            writer.writerows(data_rows)
    
    @staticmethod
    def run_ocr_on_image(image):
        ocr_result = AnalysisService.recognition_predictor([image], det_predictor=AnalysisService.detection_predictor)
        text = ocr_results_to_csv(ocr_result)
        return text

    @staticmethod
    def _summarize_with_yandexgpt(prompt: str) -> str:
        """Run YandexGPT model for summarization."""
        sdk = get_ycloud_sdk()
        model = sdk.models.completions("yandexgpt")

        try:
            result = model.run(prompt)
            return result.alternatives[0].text.strip()
        except Exception as e:
            return f"⚠️ Error during GPT call: {e}"

    @staticmethod
    def analyse_history(user_id: int) -> AnalysisResult:
        # Retrieve dummy data (you can extend with real DB query)
        df = pd.read_csv('analysis_results.csv', names=['user_id', 'date', 'analysis', 'result', 'status'])
        user_df = df[df["user_id"] == user_id]

        if user_df.empty:
            # Если нет текста для анализа, создаем специальный результат
            result = AnalysisResult(
                user_id=user_id,
                summary="Не найдено обработанных сканов для анализа. Пожалуйста, загрузите фото с помощью команды /scan.",
                generated_at=datetime.utcnow(),
            )
            # Не добавляем его в основную базу, так как это не реальный анализ
            return result
        
        previous_texts = user_df.to_string()

        prompt = (
            "Ты — ассистент врача. Проанализируй таблицу с медицинскими анализами пользователя. "
            "Выдели ключевые отклонения от нормы, укажи возможные тенденции (например, 'холестерин растет'). "
            "Дай краткую, структурированную и понятную сводку по состоянию здоровья. Не ставь диагноз, но посоветуй обратиться к врачу при наличии отклонений.\n\n"
            "История анализов:\n"
            + previous_texts
        )

        summary = AnalysisService._summarize_with_yandexgpt(prompt)

        result = AnalysisResult(
            user_id=user_id,
            summary=summary,
            generated_at=datetime.utcnow(),
        )
        results_db.append(result)
        return result

    @staticmethod
    

    @staticmethod
    def get_history(user_id: int, last_days: int | None) -> pd.DataFrame:
        df = pd.read_csv('analysis_results.csv', names=['user_id', 'date', 'analysis', 'result', 'status'])
        user_df = df[df["user_id"] == user_id]
        user_df.drop('user_id', axis=1, inplace=True)
        user_df["date"] = pd.to_datetime(user_df["date"], errors="coerce", dayfirst=True)
        if last_days is not None:
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=last_days)
            filtered = df[df["date"] >= cutoff]
            return filtered
        return user_df
    