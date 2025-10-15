from datetime import datetime, timedelta
from typing import List

from ..models.analysis_models import AnalysisScan, AnalysisResult, AnalysisHistory, AnalysesQuery
from ..utils.ycloud_client import get_ycloud_sdk

# Dummy in-memory storage
scans_db: List[AnalysisScan] = []
results_db: List[AnalysisResult] = []

class AnalysisService:

    @staticmethod
    def add_scan(user_id: int, file_id: str) -> str:
        scan = AnalysisScan(user_id=user_id, file_id=file_id, uploaded_at=datetime.utcnow())
        scans_db.append(scan)
        return f"✅ Scan received (id: {file_id})"

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
        previous = [r.summary for r in results_db if r.user_id == user_id]
        joined_text = "\n".join(previous) if previous else "Нет предыдущих анализов."

        prompt = (
            "Проанализируй историю анализов пользователя и кратко опиши состояние здоровья.\n\n"
            + joined_text
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
    def get_history(query: AnalysesQuery) -> AnalysisHistory:
        cutoff = datetime.utcnow() - query.since
        user_results = [
            r for r in results_db if r.user_id == query.user_id and r.generated_at >= cutoff
        ]
        return AnalysisHistory(user_id=query.user_id, analyses=user_results)
