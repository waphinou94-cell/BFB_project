"""
Évaluation DeepEval — comparaison ReAct vs LangGraph sur 3 questions

Usage :
    uv run python src/eval/run_eval.py

Métriques :
    RAG   → AnswerRelevancy + Faithfulness
    SQL   → AnswerRelevancy + GEval Correctness
    Mixte → AnswerRelevancy + Faithfulness
"""

import os
import time

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

from langchain_core.messages import HumanMessage
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from src.config import settings
from src.llm_factory import get_llm
from src.indexer.retriever import retrieve
from src.agent.agent_react import build_react_agent
from src.agent.agent_langgraph import build_langgraph_agent
from src.eval.dataset import RAG_CASES, SQL_CASES, MIXED_CASES, BOTH_CASES


# ─── Judge LLM ────────────────────────────────────────────────────────────────

class GeminiVertexJudge(DeepEvalBaseLLM):
    def __init__(self):
        self._llm = get_llm()

    def load_model(self):
        return self._llm

    def generate(self, prompt: str, *args, **kwargs) -> str:
        response = self._llm.invoke(prompt)
        content = response.content
        if isinstance(content, list):
            return "".join(
                p if isinstance(p, str) else p.get("text", "")
                for p in content
                if isinstance(p, (str, dict))
            )
        return str(content)

    async def a_generate(self, prompt: str, *args, **kwargs) -> str:
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return settings.llm_model


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_text(content) -> str:
    if isinstance(content, list):
        return "".join(
            p if isinstance(p, str) else p.get("text", "")
            for p in content
            if isinstance(p, (str, dict))
        )
    return str(content)


def run_agent(agent, question: str) -> dict:
    start = time.perf_counter()
    result = agent.invoke({"messages": [HumanMessage(content=question)]})
    elapsed = time.perf_counter() - start

    messages = result["messages"]

    tool_calls = sum(1 for m in messages if type(m).__name__ == "ToolMessage")

    tokens = sum(
        (m.usage_metadata or {}).get("total_tokens", 0)
        for m in messages
        if hasattr(m, "usage_metadata") and m.usage_metadata
    )

    return {
        "output": _extract_text(messages[-1].content),
        "time": elapsed,
        "tool_calls": tool_calls,
        "tokens": tokens,
    }


def get_context(query: str) -> list[str]:
    return [r["content"] for r in retrieve(query, k=5)]


def measure(metric, tc: LLMTestCase) -> tuple[float, bool]:
    try:
        metric.measure(tc)
        return metric.score, metric.score >= metric.threshold
    except Exception as e:
        print(f"    ⚠️  {metric.__class__.__name__} erreur : {e}")
        return 0.0, False


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    judge = GeminiVertexJudge()

    relevancy   = AnswerRelevancyMetric(threshold=0.5, model=judge, include_reason=False)
    faithfulness = FaithfulnessMetric(threshold=0.5, model=judge, include_reason=False)
    correctness  = GEval(
        name="Correctness",
        criteria=(
            "The actual output contains the key factual information from the expected output "
            "(monetary amounts, names, transaction counts). Minor formatting differences are acceptable."
        ),
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
        threshold=0.5,
        model=judge,
    )

    SUITE = [
        ("RAG",             RAG_CASES,   [relevancy, faithfulness]),
        ("SQL",             SQL_CASES,   [relevancy, correctness]),
        ("Mixte (chaîné)",  MIXED_CASES, [relevancy, faithfulness]),
        ("Both (parallèle)", BOTH_CASES, [relevancy, faithfulness]),
    ]

    MODES = [
        ("ReAct",      build_react_agent()),
        ("LangGraph",  build_langgraph_agent()),
    ]

    # scores[case_name][metric_name][mode_name] = (score, passed)
    scores: dict = {}
    # Collecte des réponses pour affichage
    answers: dict = {}

    print("\n" + "═" * 76)
    print("  BforBank Eval — ReAct vs LangGraph")
    print(f"  Judge : {settings.llm_model} [{settings.llm_provider}]")
    print("═" * 76)

    # perf[case_name][mode_name] = {time, tool_calls, tokens}
    perf: dict = {}

    for case_type, cases, metrics in SUITE:
        print(f"\n── {case_type} {'─' * (70 - len(case_type))}")
        for case in cases:
            name = case["name"]
            scores[name] = {}
            answers[name] = {}
            perf[name] = {}
            ctx = get_context(case["retrieval_query"]) if "retrieval_query" in case else []

            print(f"\n  Q : {case['input'][:90]}")

            for mode_name, agent in MODES:
                stats = run_agent(agent, case["input"])
                answers[name][mode_name] = stats["output"]
                perf[name][mode_name] = stats
                print(f"  [{mode_name}] {stats['output'][:100]}{'...' if len(stats['output']) > 100 else ''}")

                tc = LLMTestCase(
                    input=case["input"],
                    actual_output=stats["output"],
                    expected_output=case.get("expected_output"),
                    retrieval_context=ctx or None,
                )

                for metric in metrics:
                    mname = getattr(metric, "name", metric.__class__.__name__)
                    if mname not in scores[name]:
                        scores[name][mname] = {}
                    scores[name][mname][mode_name] = measure(metric, tc)

            # Tableau qualité
            print()
            print(f"  {'Qualité':<28} {'ReAct':>10} {'LangGraph':>12}")
            print(f"  {'─' * 28} {'─' * 10} {'─' * 12}")
            for metric in metrics:
                mname = getattr(metric, "name", metric.__class__.__name__)
                r_score, r_pass = scores[name][mname].get("ReAct", (0.0, False))
                l_score, l_pass = scores[name][mname].get("LangGraph", (0.0, False))
                r_str = f"{'✅' if r_pass else '❌'} {r_score:.2f}"
                l_str = f"{'✅' if l_pass else '❌'} {l_score:.2f}"
                print(f"  {mname:<28} {r_str:>10} {l_str:>12}")

            # Tableau performance
            print()
            print(f"  {'Performance':<28} {'ReAct':>10} {'LangGraph':>12}")
            print(f"  {'─' * 28} {'─' * 10} {'─' * 12}")
            for label, key, fmt in [
                ("Temps (s)",   "time",       lambda v: f"{v:.1f}s"),
                ("Tool calls",  "tool_calls", lambda v: str(v)),
                ("Tokens",      "tokens",     lambda v: str(v) if v > 0 else "n/d"),
            ]:
                r_val = perf[name].get("ReAct", {}).get(key, 0)
                l_val = perf[name].get("LangGraph", {}).get(key, 0)
                print(f"  {label:<28} {fmt(r_val):>10} {fmt(l_val):>12}")

    # Résumé global
    all_react = [(s, p) for cn in scores for mn in scores[cn] for s, p in [scores[cn][mn].get("ReAct", (0.0, False))]]
    all_lg    = [(s, p) for cn in scores for mn in scores[cn] for s, p in [scores[cn][mn].get("LangGraph", (0.0, False))]]

    def quality_summary(results):
        passed = sum(1 for _, p in results if p)
        avg = sum(s for s, _ in results) / len(results) if results else 0
        return passed, len(results), avg

    def perf_summary(mode):
        times  = [perf[cn][mode]["time"]       for cn in perf if mode in perf[cn]]
        tools  = [perf[cn][mode]["tool_calls"]  for cn in perf if mode in perf[cn]]
        tokens = [perf[cn][mode]["tokens"]      for cn in perf if mode in perf[cn]]
        return (
            sum(times) / len(times) if times else 0,
            sum(tools),
            sum(tokens),
        )

    rp, rt, ra = quality_summary(all_react)
    lp, lt, la = quality_summary(all_lg)
    r_time, r_tools, r_tok = perf_summary("ReAct")
    l_time, l_tools, l_tok = perf_summary("LangGraph")

    print("\n" + "═" * 76)
    print(f"  RÉSUMÉ{'':22} {'ReAct':>10} {'LangGraph':>12}")
    print(f"  {'─' * 28} {'─' * 10} {'─' * 12}")
    print(f"  {'Qualité ≥ seuil':<28} {f'{rp}/{rt}':>10} {f'{lp}/{lt}':>12}")
    print(f"  {'Score moyen':<28} {ra:>10.2f} {la:>12.2f}")
    print(f"  {'─' * 28} {'─' * 10} {'─' * 12}")
    print(f"  {'Temps moyen / question':<28} {f'{r_time:.1f}s':>10} {f'{l_time:.1f}s':>12}")
    print(f"  {'Tool calls total':<28} {r_tools:>10} {l_tools:>12}")
    print(f"  {'Tokens total':<28} {r_tok if r_tok else 'n/d':>10} {l_tok if l_tok else 'n/d':>12}")
    print("═" * 76 + "\n")


if __name__ == "__main__":
    main()
