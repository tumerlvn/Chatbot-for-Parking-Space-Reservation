"""
Example: How to use the refactored evaluate_rag_pipeline() method.

This tests the complete RAG pipeline in a SINGLE PASS including:
- Retrieval metrics (Recall@K, Precision@K, MRR) from actual production retrieval
- Generation quality (response quality scoring)
- Faithfulness (does LLM stick to retrieved docs?)
- Performance timing (total pipeline time)

Key improvement: No redundant retrieval! Metrics come from documents actually
retrieved by the production rag_node, stored in GraphState.retrieved_docs.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.chatbot.evaluation import RAGEvaluator
from src.chatbot.nodes import rag_node  # Import the actual RAG node function!


def main():
    """Run RAG pipeline evaluation."""

    print("\n" + "="*70)
    print("Running RAG Pipeline Evaluation (Single-Pass)")
    print("Testing: Production rag_node execution")
    print("Metrics extracted from GraphState.retrieved_docs")
    print("="*70 + "\n")

    # 1. Initialize evaluator
    evaluator = RAGEvaluator()

    # 2. Run evaluation with the ACTUAL rag_node function
    # This tests the real production code path in a single pass!
    # No need to pass vector_store or retriever - they're used internally by rag_node
    print("Executing rag_node for each test query...")
    metrics, results = evaluator.evaluate_rag_pipeline(
        rag_node_func=rag_node  # Pass the actual node function
    )

    # 3. Print summary
    evaluator.print_rag_pipeline_summary(metrics)

    # 4. Print detailed results for each query
    print("\nDetailed Results by Query:")
    print("-" * 70)
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['query']}")
        print(f"   Category: {result['category']}")
        print(f"   Retrieval: Recall@K={result['retrieval_recall_at_k']:.2%}, "
              f"Precision@K={result['retrieval_precision_at_k']:.2%}, MRR={result['retrieval_mrr']:.3f}")
        print(f"   Retrieved: {result['retrieved_docs_count']} docs, "
              f"{result['relevant_docs_count']} relevant")
        print(f"   Generation: Quality={result['response_quality']}, "
              f"Faithfulness={result['faithfulness_score']:.2%}")
        print(f"   Timing: Total={result['total_time']:.3f}s")
        if not result['execution_success']:
            print(f"   ⚠️  Execution FAILED")
        print(f"   Response preview: {result['response_preview']}")

    # 5. Save detailed report
    import json
    output_file = "rag_pipeline_evaluation_report.json"
    report = {
        "evaluation_type": "rag_pipeline",
        "metrics": metrics,
        "detailed_results": results
    }
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ Detailed report saved to: {output_file}")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
