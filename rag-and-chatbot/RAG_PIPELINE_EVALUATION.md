# RAG Pipeline Evaluation - Refactored Single-Pass Method

## Overview

Refactored `evaluate_rag_pipeline()` method to fix architectural flaw and address supervisor feedback: **"The evaluate_retrieval method also does not invoke the LLM chain — it benchmarks the retriever in isolation, not the RAG pipeline."**

## Architectural Improvement

### The Problem (Before)
The old evaluation performed **redundant retrieval**:
1. Phase 1: Manually called `retriever.invoke()` to get documents
2. Phase 2: Called `rag_node()` which *also* retrieved documents internally
3. Result: Tested a **different code path** than production (two separate retrievals)

### The Solution (After)
**Single-pass execution** that matches production exactly:
1. Call `rag_node()` once (production code path)
2. Extract retrieved documents from `GraphState.retrieved_docs`
3. Calculate metrics from *actual* production retrieval
4. Result: Tests the **exact same code path** users call in production

## What Changed

### Production Code Updates

1. **Added to `GraphState`**: `retrieved_docs: List[Any]` field
2. **Updated `rag_node`**: Now stores retrieved documents in state

### New Method Signature: `evaluate_rag_pipeline(rag_node_func)`

This method tests the **complete RAG pipeline** by:

1. **Single-Pass Execution** - Calls `rag_node()` once (production code path)
2. **Extract Retrieved Docs** - Gets documents from `GraphState.retrieved_docs`
3. **Test Retrieval** - Measures retrieval metrics (Recall@K, Precision@K, MRR) from extracted docs
4. **Test Generation** - Evaluates response quality (excellent/good/fair/poor)
5. **Check Faithfulness** - Verifies if LLM responses stay true to retrieved documents
6. **Measure Performance** - Total pipeline time (no artificial separation)

## Key Difference from Existing Methods

| Method | Tests Retrieval | Tests Generation | Uses Real Code Path | Use Case |
|--------|----------------|------------------|---------------------|----------|
| `evaluate_retrieval()` | ✅ Yes | ❌ No | Partial | Test if retriever finds relevant docs |
| `evaluate_end_to_end()` | ❌ No | ✅ Yes | ✅ Yes (full chatbot) | Test complete chatbot (black box) |
| **`evaluate_rag_pipeline()`** (NEW) | ✅ Yes | ✅ Yes | ✅ Yes (rag_node) | Test RAG: retrieval + generation with real code |

## Usage

```python
from chatbot.evaluation import RAGEvaluator
from chatbot.nodes import rag_node  # Import actual RAG node

evaluator = RAGEvaluator()

# Simple! Just pass the rag_node function
# No need for vector_store or retriever - rag_node handles them internally
metrics, results = evaluator.evaluate_rag_pipeline(
    rag_node_func=rag_node  # Tests real production code path!
)

# Print summary
evaluator.print_rag_pipeline_summary(metrics)
```

**Key difference:** Much simpler API! No need to pass `vector_store` and `retriever` separately because they're used internally by `rag_node`.

## Metrics Provided

### Retrieval Metrics (from actual production retrieval)
- `avg_retrieval_recall_at_k`: % of relevant docs retrieved (K = actual number retrieved by production)
- `avg_retrieval_precision_at_k`: % of retrieved docs that are relevant
- `avg_retrieval_mrr`: Mean Reciprocal Rank

### Generation Metrics
- `avg_response_quality_score`: Average quality score (0.25-1.0)
- Quality distribution: `excellent_responses`, `good_responses`, `fair_responses`, `poor_responses`

### Faithfulness Metrics
- `avg_faithfulness_score`: How well responses stick to retrieved documents (0.0-1.0)

### Overall Metrics
- `avg_total_time`: Total pipeline time (single-pass)
- `success_rate`: % of queries that completed successfully

## Example Script

Run the example:
```bash
cd rag-and-chatbot
source ../.venv/bin/activate
python example_rag_pipeline_evaluation.py
```

This will:
1. Load the vector store and retriever
2. Run evaluation using the **actual `rag_node` function**
3. Print metrics summary
4. Save detailed report to `rag_pipeline_evaluation_report.json`

## Why This Addresses Supervisor's Feedback

✅ **Invokes the LLM chain**: Calls the actual `rag_node()` function with proper GraphState
✅ **Tests real code path**: Single-pass execution exactly as in production
✅ **No redundancy**: Eliminates duplicate retrieval - uses *actual* production retrieval
✅ **Single source of truth**: Metrics come from `GraphState.retrieved_docs`
✅ **Combines retrieval + generation**: Provides both retrieval metrics AND generation quality
✅ **Comprehensive**: Includes faithfulness checking to detect hallucinations

## Technical Details

The refactored method:
1. Creates a proper `GraphState` with test query as a `HumanMessage`
2. Invokes `rag_node(state)` **once** - the actual function users call
3. Extracts retrieved documents from `result_state.retrieved_docs` (NEW!)
4. Extracts the response from `result_state.messages[-1]`
5. Calculates retrieval metrics using *only* the extracted documents
6. Evaluates response quality against expected phrases
7. Checks faithfulness using *only* the extracted documents

This ensures we're testing the **exact production code path** with **zero redundancy**.
