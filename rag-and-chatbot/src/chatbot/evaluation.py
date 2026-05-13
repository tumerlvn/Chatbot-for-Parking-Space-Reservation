"""RAG system evaluation: retrieval accuracy, response time, quality metrics."""

import time
import json
import logging
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, asdict

from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Single evaluation result with retrieval and quality metrics."""
    query: str
    retrieved_docs: int
    relevant_docs: int
    recall_at_3: float
    precision_at_3: float
    recall_at_10: float
    precision_at_10: float
    mrr: float
    retrieval_time: float
    total_time: float
    response_quality: str


class RAGEvaluator:
    """Evaluate RAG system performance with test queries and ground truth."""

    def __init__(self):
        """Initialize evaluator with test dataset."""
        self.test_cases = self._create_test_dataset()

    def _create_test_dataset(self) -> List[Dict]:
        """Create test dataset with queries, keywords, and expected answers."""
        return [
            {
                "query": "What are your operating hours?",
                "relevant_keywords": ["24 hours", "8:00 AM", "8:00 PM", "open"],
                "expected_answer_contains": ["24 hours", "24/7", "8 AM", "8 PM"],
                "category": "policy",
            },
            {
                "query": "How much does parking cost per hour?",
                "relevant_keywords": ["$5.00", "hour", "price", "rate"],
                "expected_answer_contains": ["$5", "hour"],
                "category": "pricing",
            },
            {
                "query": "Do you have EV charging?",
                "relevant_keywords": ["EV", "electric", "Level 2", "charging"],
                "expected_answer_contains": ["EV", "Level 2", "Row A"],
                "category": "amenities",
            },
            {
                "query": "Can I park my RV here?",
                "relevant_keywords": ["RV", "prohibited", "vehicle", "accept"],
                "expected_answer_contains": ["RV", "prohibited", "not"],
                "category": "restrictions",
            },
            {
                "query": "What is the cancellation policy?",
                "relevant_keywords": ["cancellation", "30 minutes", "$5.00", "fee"],
                "expected_answer_contains": ["30 minutes", "$5", "cancel"],
                "category": "policy",
            },
            {
                "query": "Where are accessible parking spots?",
                "relevant_keywords": ["accessible", "Ground Floor", "elevator"],
                "expected_answer_contains": ["Ground", "accessible"],
                "category": "amenities",
            },
            {
                "query": "What's the daily maximum charge?",
                "relevant_keywords": ["daily", "$35", "maximum", "24-hour"],
                "expected_answer_contains": ["$35", "daily"],
                "category": "pricing",
            },
            {
                "query": "Is there 24/7 security?",
                "relevant_keywords": ["security", "CCTV", "surveillance", "24/7"],
                "expected_answer_contains": ["security", "24/7", "CCTV"],
                "category": "amenities",
            },
            {
                "query": "Can I modify my reservation?",
                "relevant_keywords": ["modification", "1 hour", "change", "reservation"],
                "expected_answer_contains": ["modify", "1 hour", "hour before"],
                "category": "policy",
            },
            {
                "query": "What is the overnight rate?",
                "relevant_keywords": ["overnight", "$15", "6:00 PM", "8:00 AM"],
                "expected_answer_contains": ["$15", "overnight", "6 PM", "8 AM"],
                "category": "pricing",
            },
        ]

    def evaluate_retrieval(
        self,
        vector_store,
        retriever,
        k_values: List[int] = [3, 10]
    ) -> Dict[str, float]:
        """Evaluate retrieval accuracy with Recall@K, Precision@K, and MRR."""
        results = []

        for test_case in self.test_cases:
            query = test_case["query"]
            relevant_keywords = test_case["relevant_keywords"]

            # Time the retrieval
            start_time = time.time()

            # Get base retrieval (k=10)
            base_docs = vector_store.similarity_search(query, k=10)

            # Get reranked results (top 3)
            reranked_docs = retriever.invoke(query)

            retrieval_time = time.time() - start_time

            # Calculate relevance for each retrieved document
            def is_relevant(doc, keywords):
                content = doc.page_content.lower()
                return any(keyword.lower() in content for keyword in keywords)

            # Count actual relevant documents for this query (not keywords)
            # Note: In a real scenario, you'd have ground truth relevant doc IDs
            # Here we approximate by counting docs that contain relevant keywords
            relevant_in_3 = sum(1 for doc in reranked_docs if is_relevant(doc, relevant_keywords))
            relevant_in_10 = sum(1 for doc in base_docs if is_relevant(doc, relevant_keywords))

            # Total relevant documents = count of actually relevant docs found in top-10
            # This is an approximation; ideally you'd have ground truth
            total_relevant_docs = relevant_in_10

            # Metrics for k=3 (reranked)
            recall_at_3 = relevant_in_3 / total_relevant_docs if total_relevant_docs > 0 else 0
            precision_at_3 = relevant_in_3 / len(reranked_docs) if len(reranked_docs) > 0 else 0

            # Metrics for k=10 (base retrieval)
            recall_at_10 = relevant_in_10 / total_relevant_docs if total_relevant_docs > 0 else 0
            precision_at_10 = relevant_in_10 / len(base_docs) if len(base_docs) > 0 else 0

            # MRR: Position of first relevant document
            mrr = 0
            for i, doc in enumerate(reranked_docs, 1):
                if is_relevant(doc, relevant_keywords):
                    mrr = 1 / i
                    break

            result = EvaluationResult(
                query=query,
                retrieved_docs=len(reranked_docs),
                relevant_docs=relevant_in_3,
                recall_at_3=recall_at_3,
                precision_at_3=precision_at_3,
                recall_at_10=recall_at_10,
                precision_at_10=precision_at_10,
                mrr=mrr,
                retrieval_time=retrieval_time,
                total_time=retrieval_time,
                response_quality="not_evaluated"
            )

            results.append(result)

        # Calculate averages
        avg_metrics = {
            "avg_recall_at_3": sum(r.recall_at_3 for r in results) / len(results),
            "avg_precision_at_3": sum(r.precision_at_3 for r in results) / len(results),
            "avg_recall_at_10": sum(r.recall_at_10 for r in results) / len(results),
            "avg_precision_at_10": sum(r.precision_at_10 for r in results) / len(results),
            "avg_mrr": sum(r.mrr for r in results) / len(results),
            "avg_retrieval_time": sum(r.retrieval_time for r in results) / len(results),
            "total_queries": len(results),
        }

        return avg_metrics, results

    def evaluate_end_to_end(
        self,
        chatbot
    ) -> Tuple[Dict[str, float], List[EvaluationResult]]:
        """Evaluate end-to-end chatbot performance with response time and quality."""
        results = []

        for test_case in self.test_cases:
            query = test_case["query"]
            expected_contains = test_case["expected_answer_contains"]

            # Reset chatbot for each query
            chatbot.reset()

            # Time the full response
            start_time = time.time()
            response = chatbot.chat(query)
            total_time = time.time() - start_time

            # Check if response contains expected phrases
            response_lower = response.lower()
            contains_count = sum(
                1 for phrase in expected_contains
                if phrase.lower() in response_lower
            )

            response_quality = (
                "excellent" if contains_count >= len(expected_contains) * 0.8 else
                "good" if contains_count >= len(expected_contains) * 0.6 else
                "fair" if contains_count >= len(expected_contains) * 0.4 else
                "poor"
            )

            result = EvaluationResult(
                query=query,
                retrieved_docs=0,  # Not tracked in end-to-end
                relevant_docs=contains_count,
                recall_at_3=0,  # Not applicable
                precision_at_3=0,  # Not applicable
                recall_at_10=0,
                precision_at_10=0,
                mrr=0,
                retrieval_time=0,  # Not tracked separately
                total_time=total_time,
                response_quality=response_quality
            )

            results.append(result)

        # Calculate metrics
        quality_scores = {
            "excellent": 1.0,
            "good": 0.75,
            "fair": 0.5,
            "poor": 0.25
        }

        avg_quality = sum(quality_scores[r.response_quality] for r in results) / len(results)

        metrics = {
            "avg_response_time": sum(r.total_time for r in results) / len(results),
            "avg_quality_score": avg_quality,
            "excellent_responses": sum(1 for r in results if r.response_quality == "excellent"),
            "good_responses": sum(1 for r in results if r.response_quality == "good"),
            "fair_responses": sum(1 for r in results if r.response_quality == "fair"),
            "poor_responses": sum(1 for r in results if r.response_quality == "poor"),
            "total_queries": len(results),
        }

        return metrics, results

    def evaluate_rag_pipeline(
        self,
        rag_node_func
    ) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
        """
        Evaluate complete RAG pipeline: retrieval + generation.

        Tests the actual RAG node in a single pass exactly as it runs in production.
        Retrieval metrics are extracted from the retrieved_docs field in GraphState.

        Args:
            rag_node_func: The actual rag_node function from the graph

        Returns:
            Tuple of (aggregated metrics dict, detailed results list)
        """
        results = []

        for test_case in self.test_cases:
            query = test_case["query"]
            relevant_keywords = test_case["relevant_keywords"]
            expected_contains = test_case["expected_answer_contains"]

            # Create proper GraphState as the rag_node expects
            from .state import GraphState, ReservationData

            test_state = GraphState(
                messages=[HumanMessage(content=query)],
                intent="question",
                reservation_data=ReservationData(),
                next_action=None,
                thread_id="eval_test",
                retrieved_docs=[]
            )

            # SINGLE-PASS EXECUTION: Call the actual rag_node (production code path)
            start_time = time.time()
            try:
                result_dict = rag_node_func(test_state)
                total_time = time.time() - start_time

                # Convert dict result back to GraphState for uniform access
                # Nodes return dicts for LangGraph compatibility
                result_state = GraphState(**result_dict) if isinstance(result_dict, dict) else result_dict

                # Extract response from state
                last_message = result_state.messages[-1]
                response = last_message.content if hasattr(last_message, 'content') else str(last_message)

                # Extract retrieved documents from state (single source of truth!)
                retrieved_docs = result_state.retrieved_docs if hasattr(result_state, 'retrieved_docs') else []

                execution_success = True
            except Exception as e:
                logger.error(f"RAG node invocation failed for query '{query}': {e}")
                response = ""
                retrieved_docs = []
                total_time = time.time() - start_time
                execution_success = False

            # EVALUATE RETRIEVAL: Calculate metrics from extracted documents
            def is_relevant(doc, keywords):
                """Check if document is relevant based on keyword matching."""
                if not doc or not hasattr(doc, 'page_content'):
                    return False
                content = doc.page_content.lower()
                # Check if any keyword appears in content
                return any(keyword.lower() in content for keyword in keywords)

            # Count relevant documents in retrieved set
            relevant_docs_count = sum(1 for doc in retrieved_docs if is_relevant(doc, relevant_keywords))
            retrieved_count = len(retrieved_docs)

            # Calculate retrieval metrics (using k = number of docs retrieved by production code)
            # For recall: we approximate total relevant as the number found (since we don't have ground truth)
            total_relevant_estimate = relevant_docs_count if relevant_docs_count > 0 else 1

            recall_at_k = relevant_docs_count / total_relevant_estimate if retrieved_count > 0 else 0
            precision_at_k = relevant_docs_count / retrieved_count if retrieved_count > 0 else 0

            # MRR: Position of first relevant document
            mrr = 0
            for i, doc in enumerate(retrieved_docs, 1):
                if is_relevant(doc, relevant_keywords):
                    mrr = 1 / i
                    break

            # EVALUATE GENERATION: Check response quality
            response_lower = response.lower()
            contains_count = sum(
                1 for phrase in expected_contains
                if phrase.lower() in response_lower
            )

            response_quality = (
                "excellent" if contains_count >= len(expected_contains) * 0.8 else
                "good" if contains_count >= len(expected_contains) * 0.6 else
                "fair" if contains_count >= len(expected_contains) * 0.4 else
                "poor"
            )

            # EVALUATE FAITHFULNESS: Does response stick to retrieved docs?
            faithfulness_score = 0.0
            if retrieved_docs and response:
                # Check if response content appears in retrieved docs
                retrieved_content = " ".join([
                    doc.page_content.lower()
                    for doc in retrieved_docs
                    if hasattr(doc, 'page_content')
                ])

                # Count how many expected phrases are in BOTH response AND retrieved docs
                faithful_count = sum(
                    1 for phrase in expected_contains
                    if phrase.lower() in response_lower and phrase.lower() in retrieved_content
                )
                faithfulness_score = faithful_count / len(expected_contains) if expected_contains else 0.0

            # Store combined result
            result = {
                "query": query,
                "category": test_case["category"],
                # Retrieval metrics (from actual production retrieval)
                "retrieval_recall_at_k": recall_at_k,
                "retrieval_precision_at_k": precision_at_k,
                "retrieval_mrr": mrr,
                "retrieved_docs_count": retrieved_count,
                "relevant_docs_count": relevant_docs_count,
                # Generation metrics
                "response_quality": response_quality,
                "expected_phrases_found": contains_count,
                "expected_phrases_total": len(expected_contains),
                "faithfulness_score": faithfulness_score,
                "execution_success": execution_success,
                # Timing (single-pass, no separate phases)
                "total_time": total_time,
                # Debug info
                "response_preview": response[:200] if response else "N/A"
            }

            results.append(result)

        # Calculate aggregate metrics
        successful_results = [r for r in results if r["execution_success"]]

        if not successful_results:
            logger.error("No successful RAG pipeline evaluations!")
            return {}, results

        quality_scores = {
            "excellent": 1.0,
            "good": 0.75,
            "fair": 0.5,
            "poor": 0.25
        }

        avg_metrics = {
            # Retrieval metrics (from actual production retrieval)
            "avg_retrieval_recall_at_k": sum(r["retrieval_recall_at_k"] for r in successful_results) / len(successful_results),
            "avg_retrieval_precision_at_k": sum(r["retrieval_precision_at_k"] for r in successful_results) / len(successful_results),
            "avg_retrieval_mrr": sum(r["retrieval_mrr"] for r in successful_results) / len(successful_results),

            # Generation metrics
            "avg_response_quality_score": sum(quality_scores[r["response_quality"]] for r in successful_results) / len(successful_results),
            "excellent_responses": sum(1 for r in successful_results if r["response_quality"] == "excellent"),
            "good_responses": sum(1 for r in successful_results if r["response_quality"] == "good"),
            "fair_responses": sum(1 for r in successful_results if r["response_quality"] == "fair"),
            "poor_responses": sum(1 for r in successful_results if r["response_quality"] == "poor"),

            # Faithfulness
            "avg_faithfulness_score": sum(r["faithfulness_score"] for r in successful_results) / len(successful_results),

            # Timing (single-pass)
            "avg_total_time": sum(r["total_time"] for r in successful_results) / len(successful_results),

            # Overall
            "total_queries": len(results),
            "successful_queries": len(successful_results),
            "success_rate": len(successful_results) / len(results) if results else 0
        }

        return avg_metrics, results

    def generate_report(
        self,
        retrieval_metrics: Dict,
        retrieval_results: List[EvaluationResult],
        e2e_metrics: Dict,
        e2e_results: List[EvaluationResult],
        output_file: str = "evaluation_report.json"
    ):
        """Generate comprehensive evaluation report and save to JSON."""
        report = {
            "evaluation_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "retrieval_evaluation": {
                "metrics": retrieval_metrics,
                "detailed_results": [asdict(r) for r in retrieval_results]
            },
            "end_to_end_evaluation": {
                "metrics": e2e_metrics,
                "detailed_results": [asdict(r) for r in e2e_results]
            },
            "summary": {
                "retrieval_performance": "Excellent" if retrieval_metrics["avg_recall_at_3"] > 0.8 else "Good" if retrieval_metrics["avg_recall_at_3"] > 0.6 else "Needs Improvement",
                "response_quality": "Excellent" if e2e_metrics["avg_quality_score"] > 0.8 else "Good" if e2e_metrics["avg_quality_score"] > 0.6 else "Needs Improvement",
                "response_time": "Fast" if e2e_metrics["avg_response_time"] < 2.0 else "Moderate" if e2e_metrics["avg_response_time"] < 4.0 else "Slow"
            }
        }

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        return report

    def print_summary(self, retrieval_metrics: Dict, e2e_metrics: Dict):
        """Print evaluation summary to console."""
        logger.info("="*70)
        logger.info("RAG SYSTEM EVALUATION SUMMARY")
        logger.info("="*70)

        logger.info(" RETRIEVAL METRICS:")
        logger.info(f"  Recall@3:     {retrieval_metrics['avg_recall_at_3']:.2%}")
        logger.info(f"  Precision@3:  {retrieval_metrics['avg_precision_at_3']:.2%}")
        logger.info(f"  Recall@10:    {retrieval_metrics['avg_recall_at_10']:.2%}")
        logger.info(f"  Precision@10: {retrieval_metrics['avg_precision_at_10']:.2%}")
        logger.info(f"  MRR:          {retrieval_metrics['avg_mrr']:.3f}")
        logger.info(f"  Avg Time:     {retrieval_metrics['avg_retrieval_time']:.3f}s")

        logger.info(" END-TO-END METRICS:")
        logger.info(f"  Avg Response Time:  {e2e_metrics['avg_response_time']:.3f}s")
        logger.info(f"  Avg Quality Score:  {e2e_metrics['avg_quality_score']:.2%}")
        logger.info(f"  Excellent:          {e2e_metrics['excellent_responses']}/{e2e_metrics['total_queries']}")
        logger.info(f"  Good:               {e2e_metrics['good_responses']}/{e2e_metrics['total_queries']}")
        logger.info(f"  Fair:               {e2e_metrics['fair_responses']}/{e2e_metrics['total_queries']}")
        logger.info(f"  Poor:               {e2e_metrics['poor_responses']}/{e2e_metrics['total_queries']}")

        logger.info("="*70)

    def print_rag_pipeline_summary(self, metrics: Dict):
        """Print RAG pipeline evaluation summary to console."""
        logger.info("="*70)
        logger.info("RAG PIPELINE EVALUATION SUMMARY (Single-Pass)")
        logger.info("="*70)

        logger.info(" RETRIEVAL METRICS (from production retrieval):")
        logger.info(f"  Recall@K:     {metrics['avg_retrieval_recall_at_k']:.2%}")
        logger.info(f"  Precision@K:  {metrics['avg_retrieval_precision_at_k']:.2%}")
        logger.info(f"  MRR:          {metrics['avg_retrieval_mrr']:.3f}")

        logger.info(" GENERATION METRICS:")
        logger.info(f"  Avg Quality Score:  {metrics['avg_response_quality_score']:.2%}")
        logger.info(f"  Excellent:          {metrics['excellent_responses']}/{metrics['total_queries']}")
        logger.info(f"  Good:               {metrics['good_responses']}/{metrics['total_queries']}")
        logger.info(f"  Fair:               {metrics['fair_responses']}/{metrics['total_queries']}")
        logger.info(f"  Poor:               {metrics['poor_responses']}/{metrics['total_queries']}")

        logger.info(" FAITHFULNESS:")
        logger.info(f"  Avg Faithfulness:   {metrics['avg_faithfulness_score']:.2%}")

        logger.info(" OVERALL:")
        logger.info(f"  Avg Pipeline Time:  {metrics['avg_total_time']:.3f}s")
        logger.info(f"  Success Rate:       {metrics['success_rate']:.2%}")

        logger.info("="*70)
