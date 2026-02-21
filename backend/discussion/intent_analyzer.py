"""Intent Analyzer - Converts natural language to structured requirements."""

import json
import logging
from dataclasses import dataclass, field

from backend.pipeline.llm_router import LLMResponse, LLMRouter, TaskComplexity, llm_router

logger = logging.getLogger(__name__)

INTENT_ANALYSIS_PROMPT = """당신은 사용자의 자연어 요청을 분석하는 Intent Analyzer입니다.

사용자 입력을 분석하여 다음 JSON 형식으로 구조화해주세요:

```json
{
    "task": "작업 유형 (sentiment_analysis, data_collection, comparison, ...)",
    "source_type": "데이터 소스 유형 (web_reviews, api, pdf, file, database, none)",
    "source_hints": ["구체적 소스 힌트 (예: naver_shopping, google_play 등)"],
    "output_format": "출력 형식 (report, table, chart, json, text)",
    "needs_clarification": false,
    "clarification_questions": [],
    "confidence": 0.85,
    "estimated_complexity": "simple|standard|complex",
    "summary": "요청 요약 (한국어)"
}
```

규칙:
1. 모호한 요청이면 needs_clarification=true로 설정하고 clarification_questions에 질문을 추가하세요.
2. confidence는 0.0~1.0 사이 값으로, 분석 확실성을 나타냅니다.
3. 항상 유효한 JSON만 출력하세요. 다른 텍스트를 포함하지 마세요.
4. 한국어와 영어 입력 모두 처리할 수 있어야 합니다.
"""


@dataclass
class IntentResult:
    """Parsed intent analysis result."""

    task: str = "custom"
    source_type: str = "none"
    source_hints: list[str] = field(default_factory=list)
    output_format: str = "text"
    needs_clarification: bool = False
    clarification_questions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    estimated_complexity: str = "simple"
    summary: str = ""
    raw_response: str = ""


class IntentAnalyzer:
    """Analyzes user input and extracts structured intent."""

    def __init__(self, router: LLMRouter | None = None):
        self.router = router or llm_router

    async def analyze(self, user_input: str) -> IntentResult:
        """Analyze user input and return structured intent."""
        messages = [
            {"role": "system", "content": INTENT_ANALYSIS_PROMPT},
            {"role": "user", "content": user_input},
        ]

        try:
            response: LLMResponse = await self.router.generate(
                messages=messages,
                complexity=TaskComplexity.SIMPLE,  # Intent analysis is lightweight
                temperature=0.3,  # Low temperature for consistent parsing
                max_tokens=1024,
            )

            return self._parse_response(response.content)
        except RuntimeError:
            # No LLM available - fall back to pattern matching
            logger.warning("No LLM available, using pattern matching fallback")
            return self._pattern_match_fallback(user_input)
        except Exception as e:
            # Catch any API errors (openai, anthropic, httpx, etc.)
            logger.error(f"LLM API error during intent analysis: {e}")
            return self._pattern_match_fallback(user_input)

    def _parse_response(self, content: str) -> IntentResult:
        """Parse LLM response into IntentResult."""
        try:
            # Try to extract JSON from response
            json_str = content.strip()
            # Handle markdown code blocks
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)
            return IntentResult(
                task=data.get("task", "custom"),
                source_type=data.get("source_type", "none"),
                source_hints=data.get("source_hints", []),
                output_format=data.get("output_format", "text"),
                needs_clarification=data.get("needs_clarification", False),
                clarification_questions=data.get("clarification_questions", []),
                confidence=data.get("confidence", 0.5),
                estimated_complexity=data.get("estimated_complexity", "simple"),
                summary=data.get("summary", ""),
                raw_response=content,
            )
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"Failed to parse intent response: {e}")
            return IntentResult(
                task="custom",
                needs_clarification=True,
                clarification_questions=["요청을 더 구체적으로 설명해주시겠어요?"],
                confidence=0.1,
                raw_response=content,
            )

    def _pattern_match_fallback(self, user_input: str) -> IntentResult:
        """Simple pattern matching when LLM is unavailable."""
        input_lower = user_input.lower()

        # Detect task type
        task = "custom"
        if any(kw in input_lower for kw in ["감성", "감정", "sentiment", "리뷰 분석"]):
            task = "sentiment_analysis"
        elif any(kw in input_lower for kw in ["수집", "크롤링", "crawl", "scrape", "긁어"]):
            task = "data_collection"
        elif any(kw in input_lower for kw in ["비교", "compare", "vs"]):
            task = "comparison"
        elif any(kw in input_lower for kw in ["리포트", "보고서", "report"]):
            task = "report_generation"
        elif any(kw in input_lower for kw in ["번역", "translate"]):
            task = "translation"
        elif any(kw in input_lower for kw in ["요약", "summarize", "요약해"]):
            task = "summarization"

        # Detect source type
        source_type = "none"
        source_hints: list[str] = []
        if any(kw in input_lower for kw in ["네이버", "naver"]):
            source_type = "web_reviews"
            source_hints.append("naver")
        elif any(kw in input_lower for kw in ["url", "http", "웹", "사이트", "web"]):
            source_type = "web_reviews"
        elif any(kw in input_lower for kw in ["pdf"]):
            source_type = "pdf"
        elif any(kw in input_lower for kw in ["csv", "excel", "엑셀", "파일"]):
            source_type = "file"
        elif any(kw in input_lower for kw in ["api"]):
            source_type = "api"

        # Detect output format
        output_format = "text"
        if any(kw in input_lower for kw in ["리포트", "보고서", "report"]):
            output_format = "report"
        elif any(kw in input_lower for kw in ["표", "table", "테이블"]):
            output_format = "table"
        elif any(kw in input_lower for kw in ["차트", "chart", "그래프"]):
            output_format = "chart"
        elif any(kw in input_lower for kw in ["json"]):
            output_format = "json"

        # Estimate complexity
        word_count = len(user_input.split())
        if word_count > 50 or task == "comparison":
            complexity = "complex"
        elif word_count > 20 or task in ("report_generation", "data_collection"):
            complexity = "standard"
        else:
            complexity = "simple"

        confidence = 0.7 if task != "custom" else 0.3

        return IntentResult(
            task=task,
            source_type=source_type,
            source_hints=source_hints,
            output_format=output_format,
            needs_clarification=task == "custom",
            clarification_questions=["어떤 작업을 수행하고 싶으신가요?"]
            if task == "custom"
            else [],
            confidence=confidence,
            estimated_complexity=complexity,
            summary=f"[패턴매칭] {task}: {user_input[:50]}...",
        )
