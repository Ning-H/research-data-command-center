# Seed Research Program: Structured Technical Study-Material Generation

Status: active seed research program

## Origin

This program starts from a real product experience: a user asked a frontier model
to generate study material for Python algorithms. The task should be standard:
explain what each algorithm is, when to use it, show code patterns, include
LeetCode-style examples, and organize the material into a coherent learning
guide. The output was disappointing because it was shallow, uneven, and
under-specified. The model generated text fluently, but the final document did
not behave like a strong study artifact.

## Research Program

```text
Improve structured technical study-material generation for Python algorithms
interview preparation.
```

## Research Goal

Improve the model's ability to produce complete, pedagogically useful, structured
technical documents from simple user intent. The target behavior is not just
longer answers. The target is better coverage, depth, examples, ordering,
accuracy, and usefulness.

## Hypothesis

Models underperform on this task because general helpful-answer data rewards
short conversational responses more than complete long-form educational
artifacts. Adding high-quality study-guide examples, outline-first generation
patterns, rubric-labeled failures, and corrected examples should improve final
document usefulness.

## Data Assets

Use real public or generated data first:

- `PUBLIC_REAL`: public Python tutorial and algorithm reference material where
  license permits use.
- `PUBLIC_REAL`: public coding problem metadata and descriptions where license
  permits use.
- `PUBLIC_REAL`: public instruction-tuning and coding datasets already registered
  in the data asset catalog.
- `GENERATED_REAL`: model-generated study guides from baseline and candidate
  model versions.
- `GENERATED_REAL`: rubric scores computed by our evaluation runner.
- `SYNTHETIC_REALISTIC`: reviewer names, triage status, review notes, and
  severity labels only.

## Experiment Variants

1. Baseline instruction model generates a Python algorithms guide from one
   simple prompt.
2. Variant A adds structured study-guide examples.
3. Variant B adds outline-first planning examples.
4. Variant C adds corrected failures from previous evals.
5. Variant D balances concise explanations with required depth and examples.

## Evaluation Rubric

The evaluation suite should measure:

- Coverage: arrays, strings, hash maps, stacks, queues, linked lists, trees,
  graphs, heaps, sorting, binary search, intervals, backtracking, dynamic
  programming, greedy methods, and union find.
- Depth: each topic explains the concept, use cases, pattern recognition, and
  complexity.
- Example quality: each section includes representative code patterns and
  practice problems.
- Learning progression: beginner concepts appear before advanced combinations.
- Accuracy: definitions, complexity analysis, and code examples are correct.
- Document usefulness: the final artifact can actually support study and review.

## Failure Taxonomy

- Missing major algorithm category
- Shallow explanation
- No code pattern
- No practice example
- Incorrect complexity analysis
- Poor learning order
- Repetitive filler
- Too verbose but low substance
- Inaccurate example solution
- Weak final document structure

## Product Mapping

- Research Programs: stores this program, hypothesis, goals, and decision notes.
- Data Assets: stores public coding/education data and generated study-guide
  outputs.
- Experiments: compares baseline, structured-example, outline-first, and
  failure-replay variants.
- Training Runs: stores externally executed fine-tuning run metadata, metrics,
  and checkpoints.
- Models & Checkpoints: promotes the best checkpoint into a candidate model
  version.
- Evaluations: stores rubric scores and generated study-guide outputs.
- Inference Observability: stores long-form document generation traces,
  latency, token counts, and prompt/response metadata.
- Failure Library: stores failed sections and rubric explanations.
- Dataset Iterations: turns reviewed failures into examples for the next data
  version.
- Workspace: gives researchers a review queue for failures, dataset candidates,
  and promotion decisions.
