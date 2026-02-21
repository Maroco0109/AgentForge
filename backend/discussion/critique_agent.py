"""Critique Agent - Critically analyzes design proposals."""

import json
import logging

from pydantic import BaseModel, Field

from backend.discussion.design_generator import DesignProposal
from backend.pipeline.llm_router import LLMResponse, LLMRouter, TaskComplexity, llm_router

logger = logging.getLogger(__name__)

CRITIQUE_PROMPT = """You are a critical design reviewer (Devil's Advocate).
Your job is to find problems, risks, and weaknesses in pipeline designs.

Analyze each design proposal from these perspectives:
1. **Weaknesses**: Structural or logical weaknesses
2. **Risks**: What could go wrong in production
3. **Edge Cases**: Scenarios the design doesn't handle
4. **Security**: Potential security vulnerabilities
5. **Cost**: Cost-related concerns and hidden costs
6. **Scalability**: How the design handles growth

For each design, provide an overall score from 0.0 to 1.0 and a summary recommendation.

Return ONLY valid JSON in this format:
```json
{
    "critiques": [
        {
            "design_name": "Name of the design",
            "weaknesses": ["weakness 1", "weakness 2"],
            "risks": ["risk 1"],
            "edge_cases": ["edge case 1"],
            "security_concerns": ["concern 1"],
            "cost_concerns": ["cost issue 1"],
            "scalability_notes": ["note 1"],
            "overall_score": 0.75,
            "recommendation": "Summary recommendation"
        }
    ]
}
```

Be thorough but fair. Not every design needs to score poorly -
simple designs can score well for simple tasks.
"""


class CritiqueResult(BaseModel):
    """Result of critiquing a single design proposal."""

    design_name: str
    weaknesses: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    security_concerns: list[str] = Field(default_factory=list)
    cost_concerns: list[str] = Field(default_factory=list)
    scalability_notes: list[str] = Field(default_factory=list)
    overall_score: float = 0.5  # 0.0 - 1.0
    recommendation: str = ""


class CritiqueAgent:
    """Critically analyzes design proposals to find problems and risks."""

    def __init__(self, router: LLMRouter | None = None):
        self.router = router or llm_router

    async def critique_designs(
        self, designs: list[DesignProposal], requirements: dict
    ) -> list[CritiqueResult]:
        """Critique each design proposal using LLM.

        Args:
            designs: List of design proposals to critique.
            requirements: Original requirements for context.

        Returns:
            List of critique results, one per design.
        """
        user_content = self._build_critique_prompt(designs, requirements)
        messages = [
            {"role": "system", "content": CRITIQUE_PROMPT},
            {"role": "user", "content": user_content},
        ]

        try:
            response: LLMResponse = await self.router.generate(
                messages=messages,
                complexity=TaskComplexity.STANDARD,
                temperature=0.5,
                max_tokens=4096,
            )
            return self._parse_critiques(response.content, designs)
        except RuntimeError:
            logger.warning("No LLM available, using fallback critique")
            return self.critique_designs_fallback(designs, requirements)
        except Exception as e:
            logger.error(f"LLM API error during critique: {e}")
            return self.critique_designs_fallback(designs, requirements)

    def critique_designs_fallback(
        self, designs: list[DesignProposal], requirements: dict
    ) -> list[CritiqueResult]:
        """Rule-based fallback critique without LLM.

        Applies heuristic rules to evaluate designs.
        """
        results: list[CritiqueResult] = []
        task_complexity = requirements.get("estimated_complexity", "simple")

        for design in designs:
            weaknesses: list[str] = []
            risks: list[str] = []
            edge_cases: list[str] = []
            security_concerns: list[str] = []
            cost_concerns: list[str] = []
            scalability_notes: list[str] = []
            score = 0.7  # Base score

            agent_count = len(design.agents)

            # Check agent count
            if agent_count < 2:
                weaknesses.append("Pipeline has very few agents, limiting error recovery options")
                score -= 0.1
            elif agent_count > 5:
                weaknesses.append(
                    "Many agents increase coordination overhead and debugging complexity"
                )
                cost_concerns.append("High agent count increases per-run cost significantly")
                score -= 0.05

            # Check for missing validation
            roles = [a.role for a in design.agents]
            if "validator" not in roles and agent_count > 1:
                weaknesses.append("No data validation agent - garbage in, garbage out")
                edge_cases.append("Malformed or empty input data is not caught")
                score -= 0.1

            # Check for expensive models
            expensive_models = [
                a for a in design.agents if a.llm_model in ("gpt-4o", "claude-sonnet-4-5-20250929")
            ]
            if len(expensive_models) > 2:
                cost_concerns.append(
                    f"{len(expensive_models)} agents use expensive models - "
                    "consider if all need high-capability models"
                )

            # Security checks
            if any(a.role == "collector" for a in design.agents):
                security_concerns.append(
                    "Data collector agents should validate and sanitize external data"
                )
                edge_cases.append("External data source unavailable or rate-limited")

            # Complexity mismatch check
            if design.complexity == "high" and task_complexity == "simple":
                weaknesses.append("Design complexity exceeds task requirements - over-engineered")
                score -= 0.15
            elif design.complexity == "low" and task_complexity == "complex":
                weaknesses.append("Simple design may not handle the complexity of this task")
                score -= 0.15

            # Scalability
            if agent_count > 3:
                scalability_notes.append("Pipeline can be parallelized for better throughput")
            if all(a.llm_model == "gpt-4o-mini" for a in design.agents):
                scalability_notes.append(
                    "Using cost-effective models allows scaling to high volumes"
                )

            # General edge cases
            edge_cases.append("LLM API rate limits or temporary outages")
            if not any(a.role in ("critic", "cross_checker") for a in design.agents):
                edge_cases.append("No quality verification step - LLM hallucinations go uncaught")

            # Clamp score
            score = max(0.1, min(1.0, score))

            # Build recommendation
            if score >= 0.7:
                rec = f"{design.name} is a solid choice"
                if weaknesses:
                    rec += f", though consider addressing: {weaknesses[0]}"
            elif score >= 0.4:
                rec = f"{design.name} is viable but has notable concerns that should be addressed"
            else:
                rec = f"{design.name} needs significant improvements before deployment"

            results.append(
                CritiqueResult(
                    design_name=design.name,
                    weaknesses=weaknesses,
                    risks=risks,
                    edge_cases=edge_cases,
                    security_concerns=security_concerns,
                    cost_concerns=cost_concerns,
                    scalability_notes=scalability_notes,
                    overall_score=round(score, 2),
                    recommendation=rec,
                )
            )

        return results

    def _build_critique_prompt(self, designs: list[DesignProposal], requirements: dict) -> str:
        """Build the user prompt for critique."""
        parts = ["## Original Requirements"]
        for key, value in requirements.items():
            parts.append(f"- {key}: {value}")

        parts.append("\n## Designs to Critique")
        for i, design in enumerate(designs, 1):
            parts.append(f"\n### Design {i}: {design.name}")
            parts.append(f"Description: {design.description}")
            parts.append(f"Complexity: {design.complexity}")
            parts.append(f"Estimated Cost: {design.estimated_cost}")
            parts.append(f"Recommended: {design.recommended}")
            parts.append("Agents:")
            for agent in design.agents:
                parts.append(
                    f"  - {agent.name} ({agent.role}): {agent.description} "
                    f"[model: {agent.llm_model}]"
                )
            if design.pros:
                parts.append(f"Pros: {', '.join(design.pros)}")
            if design.cons:
                parts.append(f"Cons: {', '.join(design.cons)}")

        return "\n".join(parts)

    def _parse_critiques(self, content: str, designs: list[DesignProposal]) -> list[CritiqueResult]:
        """Parse LLM response into CritiqueResult objects."""
        try:
            json_str = content.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)
            critiques_data = data.get("critiques", [])

            results: list[CritiqueResult] = []
            for c in critiques_data:
                score = c.get("overall_score", 0.5)
                score = max(0.0, min(1.0, float(score)))
                results.append(
                    CritiqueResult(
                        design_name=c.get("design_name", "Unknown"),
                        weaknesses=c.get("weaknesses", []),
                        risks=c.get("risks", []),
                        edge_cases=c.get("edge_cases", []),
                        security_concerns=c.get("security_concerns", []),
                        cost_concerns=c.get("cost_concerns", []),
                        scalability_notes=c.get("scalability_notes", []),
                        overall_score=round(score, 2),
                        recommendation=c.get("recommendation", ""),
                    )
                )

            if not results:
                logger.warning("LLM returned empty critiques, using fallback")
                return self.critique_designs_fallback(designs, {})

            return results
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"Failed to parse critique response: {e}")
            return self.critique_designs_fallback(designs, {})
