"""Design Generator - Generates pipeline design proposals."""

import json
import logging

from pydantic import BaseModel, Field

from backend.pipeline.llm_router import LLMResponse, LLMRouter, TaskComplexity, llm_router

logger = logging.getLogger(__name__)

DESIGN_GENERATION_PROMPT = """You are a pipeline design architect.
Given user requirements, generate 2-3 pipeline design proposals.

Each design should specify:
1. A descriptive name
2. What the pipeline does
3. The agents involved (with name, role, LLM model, and description)
4. Pros and cons
5. Estimated cost per run
6. Complexity level (low/medium/high)
7. Whether you recommend this design

Return ONLY valid JSON in this format:
```json
{
    "designs": [
        {
            "name": "Design Name",
            "description": "What this design does",
            "agents": [
                {
                    "name": "agent_name",
                    "role": "collector",
                    "llm_model": "gpt-4o-mini",
                    "description": "What this agent does"
                }
            ],
            "pros": ["advantage 1", "advantage 2"],
            "cons": ["disadvantage 1"],
            "estimated_cost": "~$0.05 per run",
            "complexity": "low",
            "recommended": true
        }
    ]
}
```

Guidelines:
- Always include at least one simple/low-cost option
- Always include at least one comprehensive/high-quality option
- Use cost-effective models (gpt-4o-mini, claude-haiku) for simple tasks
- Use powerful models (gpt-4o, claude-sonnet) for complex reasoning
- Consider the user's stated preferences for cost, quality, and speed
- Respond in the same language as the user's requirements
"""


class AgentSpec(BaseModel):
    """Specification for a single agent in a pipeline design."""

    name: str
    role: str  # e.g., "collector", "analyzer", "reporter"
    llm_model: str  # e.g., "gpt-4o-mini"
    description: str


class DesignProposal(BaseModel):
    """A single pipeline design proposal."""

    name: str
    description: str
    agents: list[AgentSpec] = Field(default_factory=list)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    estimated_cost: str = "unknown"
    complexity: str = "medium"  # "low" | "medium" | "high"
    recommended: bool = False


class DesignGenerator:
    """Generates pipeline design proposals from structured requirements."""

    def __init__(self, router: LLMRouter | None = None):
        self.router = router or llm_router

    async def generate_designs(
        self, requirements: dict, context: str | None = None
    ) -> list[DesignProposal]:
        """Generate 2-3 design proposals using LLM.

        Args:
            requirements: Structured requirements from intent analysis.
            context: Optional discussion context from DiscussionMemory.

        Returns:
            List of design proposals.
        """
        user_content = self._build_requirements_prompt(requirements, context)
        messages = [
            {"role": "system", "content": DESIGN_GENERATION_PROMPT},
            {"role": "user", "content": user_content},
        ]

        try:
            response: LLMResponse = await self.router.generate(
                messages=messages,
                complexity=TaskComplexity.STANDARD,
                temperature=0.7,
                max_tokens=4096,
            )
            return self._parse_designs(response.content)
        except RuntimeError:
            logger.warning("No LLM available, using fallback design generation")
            return self.generate_designs_fallback(requirements)
        except Exception as e:
            logger.error(f"LLM API error during design generation: {e}")
            return self.generate_designs_fallback(requirements)

    def generate_designs_fallback(self, requirements: dict) -> list[DesignProposal]:
        """Pattern-based fallback without LLM.

        Generates template-based designs for common pipeline patterns.
        """
        task = requirements.get("task", "custom")
        source_type = requirements.get("source_type", "none")
        complexity = requirements.get("estimated_complexity", "simple")

        designs: list[DesignProposal] = []

        # Design 1: Simple sequential pipeline (always included)
        simple_agents = self._get_simple_agents(task, source_type)
        designs.append(
            DesignProposal(
                name="Simple Sequential Pipeline",
                description="A straightforward pipeline that processes data step by step. "
                "Best for simple tasks with predictable input.",
                agents=simple_agents,
                pros=[
                    "Low cost",
                    "Easy to debug",
                    "Fast execution",
                    "Simple to maintain",
                ],
                cons=[
                    "Limited error recovery",
                    "No parallel processing",
                    "Basic output quality",
                ],
                estimated_cost="~$0.01-0.03 per run",
                complexity="low",
                recommended=complexity == "simple",
            )
        )

        # Design 2: Standard pipeline with validation
        standard_agents = self._get_standard_agents(task, source_type)
        designs.append(
            DesignProposal(
                name="Standard Pipeline with Validation",
                description="A balanced pipeline with data validation and quality checks. "
                "Good trade-off between cost and quality.",
                agents=standard_agents,
                pros=[
                    "Data validation included",
                    "Better output quality",
                    "Error handling",
                    "Reasonable cost",
                ],
                cons=[
                    "Moderate latency",
                    "Higher cost than simple",
                    "More complex setup",
                ],
                estimated_cost="~$0.05-0.10 per run",
                complexity="medium",
                recommended=complexity == "standard",
            )
        )

        # Design 3: Advanced pipeline (for complex tasks)
        if complexity in ("standard", "complex"):
            advanced_agents = self._get_advanced_agents(task, source_type)
            designs.append(
                DesignProposal(
                    name="Advanced Multi-Agent Pipeline",
                    description="A comprehensive pipeline with specialized agents, "
                    "parallel processing, and iterative refinement.",
                    agents=advanced_agents,
                    pros=[
                        "Highest output quality",
                        "Parallel processing",
                        "Iterative refinement",
                        "Comprehensive error handling",
                    ],
                    cons=[
                        "Highest cost",
                        "Longer execution time",
                        "Complex debugging",
                    ],
                    estimated_cost="~$0.15-0.30 per run",
                    complexity="high",
                    recommended=complexity == "complex",
                )
            )

        return designs

    def _build_requirements_prompt(self, requirements: dict, context: str | None) -> str:
        """Build the user prompt from requirements and context."""
        parts = ["## Requirements"]
        for key, value in requirements.items():
            parts.append(f"- {key}: {value}")

        if context:
            parts.append(f"\n## Discussion Context\n{context}")

        return "\n".join(parts)

    def _parse_designs(self, content: str) -> list[DesignProposal]:
        """Parse LLM response into DesignProposal objects."""
        try:
            json_str = content.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)
            designs_data = data.get("designs", [])

            designs: list[DesignProposal] = []
            for d in designs_data:
                agents = [AgentSpec(**a) for a in d.get("agents", [])]
                designs.append(
                    DesignProposal(
                        name=d.get("name", "Unnamed Design"),
                        description=d.get("description", ""),
                        agents=agents,
                        pros=d.get("pros", []),
                        cons=d.get("cons", []),
                        estimated_cost=d.get("estimated_cost", "unknown"),
                        complexity=d.get("complexity", "medium"),
                        recommended=d.get("recommended", False),
                    )
                )

            if not designs:
                logger.warning("LLM returned empty designs, using fallback")
                return self.generate_designs_fallback({})

            return designs
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"Failed to parse design response: {e}")
            return self.generate_designs_fallback({})

    def _get_simple_agents(self, task: str, source_type: str) -> list[AgentSpec]:
        """Get agent specs for a simple pipeline."""
        agents: list[AgentSpec] = []

        if source_type != "none":
            agents.append(
                AgentSpec(
                    name="data_collector",
                    role="collector",
                    llm_model="gpt-4o-mini",
                    description=f"Collects data from {source_type} sources",
                )
            )

        agents.append(
            AgentSpec(
                name="processor",
                role="analyzer",
                llm_model="gpt-4o-mini",
                description=f"Processes and analyzes data for {task}",
            )
        )

        agents.append(
            AgentSpec(
                name="formatter",
                role="reporter",
                llm_model="gpt-4o-mini",
                description="Formats results into the requested output format",
            )
        )

        return agents

    def _get_standard_agents(self, task: str, source_type: str) -> list[AgentSpec]:
        """Get agent specs for a standard pipeline."""
        agents: list[AgentSpec] = []

        if source_type != "none":
            agents.append(
                AgentSpec(
                    name="data_collector",
                    role="collector",
                    llm_model="gpt-4o-mini",
                    description=f"Collects data from {source_type} sources",
                )
            )
            agents.append(
                AgentSpec(
                    name="data_validator",
                    role="validator",
                    llm_model="gpt-4o-mini",
                    description="Validates and cleans collected data",
                )
            )

        agents.append(
            AgentSpec(
                name="analyzer",
                role="analyzer",
                llm_model="gpt-4o",
                description=f"Performs detailed analysis for {task}",
            )
        )

        agents.append(
            AgentSpec(
                name="reporter",
                role="reporter",
                llm_model="gpt-4o-mini",
                description="Generates structured report with findings",
            )
        )

        return agents

    def _get_advanced_agents(self, task: str, source_type: str) -> list[AgentSpec]:
        """Get agent specs for an advanced pipeline."""
        agents: list[AgentSpec] = []

        if source_type != "none":
            agents.append(
                AgentSpec(
                    name="data_collector",
                    role="collector",
                    llm_model="gpt-4o-mini",
                    description=f"Collects data from {source_type} sources",
                )
            )
            agents.append(
                AgentSpec(
                    name="data_validator",
                    role="validator",
                    llm_model="gpt-4o-mini",
                    description="Validates, cleans, and enriches collected data",
                )
            )

        agents.append(
            AgentSpec(
                name="primary_analyzer",
                role="analyzer",
                llm_model="gpt-4o",
                description=f"Primary analysis agent for {task}",
            )
        )

        agents.append(
            AgentSpec(
                name="cross_checker",
                role="critic",
                llm_model="gpt-4o",
                description="Cross-checks analysis results for accuracy",
            )
        )

        agents.append(
            AgentSpec(
                name="synthesizer",
                role="synthesizer",
                llm_model="gpt-4o",
                description="Synthesizes findings from multiple analysis passes",
            )
        )

        agents.append(
            AgentSpec(
                name="reporter",
                role="reporter",
                llm_model="gpt-4o-mini",
                description="Generates comprehensive report with visualizations",
            )
        )

        return agents
