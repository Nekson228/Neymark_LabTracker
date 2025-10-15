from datetime import datetime, timedelta
from typing import List

from ..models.analysis_models import AnalysisScan, AnalysisResult, AnalysisHistory, AnalysesQuery

# Dummy storage
scans_db: List[AnalysisScan] = []
results_db: List[AnalysisResult] = []

class AnalysisService:

    @staticmethod
    def add_scan(user_id: int, file_id: str) -> str:
        scan = AnalysisScan(user_id=user_id, file_id=file_id, uploaded_at=datetime.utcnow())
        scans_db.append(scan)
        return f"Scan received: {file_id}"

    @staticmethod
    def analyse_history(user_id: int) -> AnalysisResult:
        # Dummy LLM summary
        summary = "Your last analyses are normal. Keep healthy!"
        result = AnalysisResult(user_id=user_id, summary=summary, generated_at=datetime.utcnow())
        results_db.append(result)
        return result

    @staticmethod
    def get_history(query: AnalysesQuery) -> AnalysisHistory:
        cutoff = datetime.utcnow() - query.since
        user_results = [
            r for r in results_db if r.user_id == query.user_id and r.generated_at >= cutoff
        ]
        return AnalysisHistory(user_id=query.user_id, analyses=user_results)
