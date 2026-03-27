"""
RAG System Evaluation Module

Evaluates:
1. Retrieval accuracy (Recall@K, Precision@K)
2. Response time performance
3. End-to-end system quality

Metrics:
- Recall@K: Of all relevant docs, what % were retrieved in top K?
- Precision@K: Of K retrieved docs, what % are relevant?
- Mean Reciprocal Rank (MRR): Position of first relevant document
- Response Time: Time to generate answer
"""

import time
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict


@dataclass
class EvaluationResult:
    """Result of a single evaluation"""
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
    """Evaluates RAG system performance"""

    def __init__(self):
        """Initialize evaluator with test dataset"""
        self.test_cases = self._create_test_dataset()

    def _create_test_dataset(self) -> List[Dict]:
        """
        Create evaluation dataset with queries and ground truth.

        Each test case has:
        - query: Test question
        - relevant_keywords: Keywords that should appear in relevant docs
        - expected_answer_contains: Phrases expected in the answer
        """
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
        """
        Evaluate retrieval accuracy.

        Args:
            vector_store: Milvus vector store
            retriever: Compression retriever with reranker
            k_values: K values for Recall@K and Precision@K

        Returns:
            Dict with average metrics across all queries
        """
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

            # Metrics for k=3 (reranked)
            relevant_in_3 = sum(1 for doc in reranked_docs if is_relevant(doc, relevant_keywords))
            total_relevant = len(relevant_keywords)  # Approximate

            recall_at_3 = relevant_in_3 / min(total_relevant, 3) if total_relevant > 0 else 0
            precision_at_3 = relevant_in_3 / 3 if len(reranked_docs) >= 3 else relevant_in_3 / len(reranked_docs) if reranked_docs else 0

            # Metrics for k=10 (base retrieval)
            relevant_in_10 = sum(1 for doc in base_docs if is_relevant(doc, relevant_keywords))

            recall_at_10 = relevant_in_10 / min(total_relevant, 10) if total_relevant > 0 else 0
            precision_at_10 = relevant_in_10 / 10 if len(base_docs) >= 10 else relevant_in_10 / len(base_docs) if base_docs else 0

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
        """
        Evaluate end-to-end chatbot performance.

        Args:
            chatbot: ParkingChatbot instance

        Returns:
            Tuple of (metrics, detailed_results)
        """
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

    def generate_report(
        self,
        retrieval_metrics: Dict,
        retrieval_results: List[EvaluationResult],
        e2e_metrics: Dict,
        e2e_results: List[EvaluationResult],
        output_file: str = "evaluation_report.json"
    ):
        """
        Generate comprehensive evaluation report.

        Args:
            retrieval_metrics: Metrics from retrieval evaluation
            retrieval_results: Detailed retrieval results
            e2e_metrics: Metrics from end-to-end evaluation
            e2e_results: Detailed end-to-end results
            output_file: Where to save the report
        """
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
        """Print evaluation summary to console"""
        print("\n" + "="*70)
        print("RAG SYSTEM EVALUATION SUMMARY")
        print("="*70)

        print("\n📊 RETRIEVAL METRICS:")
        print(f"  Recall@3:     {retrieval_metrics['avg_recall_at_3']:.2%}")
        print(f"  Precision@3:  {retrieval_metrics['avg_precision_at_3']:.2%}")
        print(f"  Recall@10:    {retrieval_metrics['avg_recall_at_10']:.2%}")
        print(f"  Precision@10: {retrieval_metrics['avg_precision_at_10']:.2%}")
        print(f"  MRR:          {retrieval_metrics['avg_mrr']:.3f}")
        print(f"  Avg Time:     {retrieval_metrics['avg_retrieval_time']:.3f}s")

        print("\n🎯 END-TO-END METRICS:")
        print(f"  Avg Response Time:  {e2e_metrics['avg_response_time']:.3f}s")
        print(f"  Avg Quality Score:  {e2e_metrics['avg_quality_score']:.2%}")
        print(f"  Excellent:          {e2e_metrics['excellent_responses']}/{e2e_metrics['total_queries']}")
        print(f"  Good:               {e2e_metrics['good_responses']}/{e2e_metrics['total_queries']}")
        print(f"  Fair:               {e2e_metrics['fair_responses']}/{e2e_metrics['total_queries']}")
        print(f"  Poor:               {e2e_metrics['poor_responses']}/{e2e_metrics['total_queries']}")

        print("\n" + "="*70)
