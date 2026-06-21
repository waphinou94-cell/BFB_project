"""
Évaluation DeepEval — comparaison ReAct vs LangGraph sur 4 questions

Usage :
    uv run python src/eval/run_eval.py

Métriques (toutes les questions ont un expected_output) :
    AnswerRelevancy  — la réponse répond-elle à la question ?
    GEval Correctness — la réponse contient-elle les faits clés de l'expected_output ?

Audit :
    eval_audit_latest.json — réponses complètes + raisons du judge, pour vérifier l'éval.
"""

import json
import os
import time
from datetime import datetime

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

from langchain_core.messages import HumanMessage
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.metrics import AnswerRelevancyMetric, GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from src.config import settings
from src.llm_factory import get_llm
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

    tool_msg_count = sum(1 for m in messages if type(m).__name__ == "ToolMessage")
    if tool_msg_count == 0 and "route" in result:
        route = result.get("route", "direct")
        tool_calls = {"rag": 1, "sql": 1, "both": 2, "direct": 0}.get(route, 0)
    else:
        tool_calls = tool_msg_count

    tokens = sum(
        (m.usage_metadata or {}).get("total_tokens", 0)
        for m in messages
        if hasattr(m, "usage_metadata") and m.usage_metadata
    )

    return {
        "output":     _extract_text(messages[-1].content),
        "time":       elapsed,
        "tool_calls": tool_calls,
        "tokens":     tokens,
        "route":      result.get("route", ""),
    }


def make_correctness_metric(judge) -> GEval:
    return GEval(
        name="Correctness",
        criteria=(
            "The actual output contains the key factual elements from the expected output: "
            "correct amounts, names, procedure references (CONF-BFB-xxx), required actions, "
            "and transaction statuses. Minor phrasing differences are acceptable. "
            "Penalize missing key facts or contradictory information."
        ),
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
        threshold=0.5,
        model=judge,
    )


def measure(metric, tc: LLMTestCase) -> tuple[float, bool, str]:
    try:
        metric.measure(tc)
        reason = getattr(metric, "reason", "") or ""
        return metric.score, metric.score >= metric.threshold, reason
    except Exception as e:
        print(f"    ⚠️  {metric.__class__.__name__} erreur : {e}")
        return 0.0, False, f"ERREUR: {e}"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    judge = GeminiVertexJudge()

    relevancy = AnswerRelevancyMetric(threshold=0.5, model=judge, include_reason=True)

    SUITE = [
        ("RAG",              RAG_CASES),
        ("SQL",              SQL_CASES),
        ("Mixte (chaîné)",   MIXED_CASES),
        ("Both (parallèle)", BOTH_CASES),
    ]

    MODES = [
        ("ReAct",     build_react_agent()),
        ("LangGraph", build_langgraph_agent()),
    ]

    scores: dict = {}
    perf: dict = {}
    audit = {
        "timestamp": datetime.now().isoformat(),
        "judge":     settings.llm_model,
        "provider":  settings.llm_provider,
        "cases":     [],
    }

    W = 88  # largeur table
    n_cases = sum(len(cases) for _, cases in SUITE)

    print("\n" + "═" * W)
    print(f"  BforBank Eval — ReAct vs LangGraph   |   Judge : {settings.llm_model} [{settings.llm_provider}]")
    print("═" * W)

    case_index = 0
    for case_type, cases in SUITE:
        for case in cases:
            case_index += 1
            name = case["name"]
            scores[name] = {}
            perf[name] = {}

            audit_case = {
                "name":            name,
                "type":            case_type,
                "input":           case["input"],
                "expected_output": case["expected_output"],
                "modes":           {},
            }

            # ── Progression minimale ──────────────────────────────────────
            q_short = case["input"][:75] + ("…" if len(case["input"]) > 75 else "")
            print(f"\n  [{case_index}/{n_cases}] {case_type.upper()} — {q_short}")

            correctness = make_correctness_metric(judge)
            metrics = [relevancy, correctness]

            for mode_name, agent in MODES:
                print(f"    → {mode_name:<10} ", end="", flush=True)
                stats = run_agent(agent, case["input"])
                perf[name][mode_name] = stats
                route_tag = f"  [route={stats['route']}]" if stats.get("route") else ""
                print(f"{stats['time']:.1f}s  {stats['tool_calls']} tool(s)  {stats['tokens'] or '?'} tok{route_tag}")

                tc = LLMTestCase(
                    input=case["input"],
                    actual_output=stats["output"],
                    expected_output=case["expected_output"],
                )

                audit_mode = {
                    "output":     stats["output"],
                    "route":      stats["route"],
                    "tool_calls": stats["tool_calls"],
                    "time_s":     round(stats["time"], 2),
                    "tokens":     stats["tokens"],
                    "metrics":    {},
                }

                for metric in metrics:
                    mname = getattr(metric, "name", metric.__class__.__name__)
                    if mname not in scores[name]:
                        scores[name][mname] = {}
                    score, passed, reason = measure(metric, tc)
                    scores[name][mname][mode_name] = (score, passed)
                    audit_mode["metrics"][mname] = {
                        "score":  round(score, 3),
                        "passed": passed,
                        "reason": reason,
                    }

                audit_case["modes"][mode_name] = audit_mode

            audit["cases"].append(audit_case)

    # ── Tableau récapitulatif complet ─────────────────────────────────────────
    #
    # colonnes : # | Type | Question | Mode | Relev | Correct | Tps | Tools | Tokens
    #
    C = {"n": 2, "type": 8, "q": 32, "mode": 14, "rel": 9, "cor": 9, "tps": 6, "tc": 5, "tok": 7}

    def row(n, typ, q, mode, rel, cor, tps, tc_, tok):
        return (
            f"  {str(n):<{C['n']}} {typ:<{C['type']}} {q:<{C['q']}} {mode:<{C['mode']}}"
            f" {rel:>{C['rel']}} {cor:>{C['cor']}} {tps:>{C['tps']}} {str(tc_):>{C['tc']}} {str(tok):>{C['tok']}}"
        )

    header = row("#", "Type", "Question", "Mode", "Relevancy", "Correct", "Tps", "TC", "Tokens")
    sep    = "  " + "─" * (W - 2)
    sep2   = "  " + "═" * (W - 2)

    print("\n" + "═" * W)
    print("  RÉSULTATS COMPLETS")
    print(sep2)
    print(header)
    print(sep)

    all_react, all_lg = [], []
    case_index = 0
    for case_type, cases in SUITE:
        for case in cases:
            case_index += 1
            name     = case["name"]
            q_label  = case["input"][:C["q"]].rstrip()
            type_short = {"RAG": "RAG", "SQL": "SQL", "Mixte (chaîné)": "Mixte", "Both (parallèle)": "Both"}.get(case_type, case_type[:8])

            for i, (mode_name, _) in enumerate(MODES):
                p = perf[name].get(mode_name, {})
                route = p.get("route", "")
                mode_label = f"{mode_name}{f'/{route}' if route else ''}"

                mnames = list(scores[name].keys())
                rel_s, rel_p = scores[name].get(mnames[0], {}).get(mode_name, (0.0, False)) if mnames else (0.0, False)
                cor_s, cor_p = scores[name].get(mnames[1], {}).get(mode_name, (0.0, False)) if len(mnames) > 1 else (0.0, False)

                rel_str = f"{'✅' if rel_p else '❌'} {rel_s:.2f}"
                cor_str = f"{'✅' if cor_p else '❌'} {cor_s:.2f}"
                tps_str = f"{p.get('time', 0):.1f}s"
                tok_str = str(p.get("tokens", 0)) + ("*" if mode_name == "LangGraph" else "")

                n_str = str(case_index) if i == 0 else ""
                t_str = type_short        if i == 0 else ""
                q_str = q_label           if i == 0 else ""

                print(row(n_str, t_str, q_str, mode_label, rel_str, cor_str, tps_str, p.get("tool_calls", 0), tok_str))

                (all_react if mode_name == "ReAct" else all_lg).extend([(rel_s, rel_p), (cor_s, cor_p)])

            if case_index < n_cases:
                print(sep)

    # ── Résumé global ─────────────────────────────────────────────────────────
    def quality_summary(results):
        passed = sum(1 for _, p in results if p)
        avg    = sum(s for s, _ in results) / len(results) if results else 0
        return passed, len(results), avg

    def perf_summary(mode):
        times  = [perf[cn][mode]["time"]       for cn in perf if mode in perf[cn]]
        tools  = [perf[cn][mode]["tool_calls"]  for cn in perf if mode in perf[cn]]
        tokens = [perf[cn][mode]["tokens"]      for cn in perf if mode in perf[cn]]
        return sum(times)/len(times) if times else 0, sum(tools), sum(tokens)

    rp, rt, ra = quality_summary(all_react)
    lp, lt, la = quality_summary(all_lg)
    r_time, r_tools, r_tok = perf_summary("ReAct")
    l_time, l_tools, l_tok = perf_summary("LangGraph")

    print(sep2)
    print(f"  {'RÉSUMÉ':<20} {'ReAct':>18} {'LangGraph':>18}")
    print(sep)
    print(f"  {'Qualité ≥ seuil':<20} {f'{rp}/{rt}':>18} {f'{lp}/{lt}':>18}")
    print(f"  {'Score moyen':<20} {ra:>18.2f} {la:>18.2f}")
    print(sep)
    print(f"  {'Temps moyen / Q':<20} {f'{r_time:.1f}s':>18} {f'{l_time:.1f}s':>18}")
    print(f"  {'Tool calls total':<20} {r_tools:>18} {l_tools:>18}")
    print(f"  {'Tokens total':<20} {f'{r_tok}':>18} {f'{l_tok}*':>18}")
    print(sep2)
    print(f"  * LangGraph : tokens du nœud router non comptabilisés\n")

    audit_path = "eval_audit_latest.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)
    print(f"  Audit → {audit_path}\n")


if __name__ == "__main__":
    main()
