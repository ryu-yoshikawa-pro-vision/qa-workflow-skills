from . import (
    adversarial_review,
    coverage_analysis,
    qa_workflow,
    question_analysis,
    spec_analysis,
    test_analysis,
    test_case_design,
    test_condition_design,
    test_requirement_design,
)

VALIDATORS = {
    "qa-workflow": qa_workflow.validate,
    "spec-analysis": spec_analysis.validate,
    "question-analysis": question_analysis.validate,
    "test-analysis": test_analysis.validate,
    "test-requirement-design": test_requirement_design.validate,
    "test-condition-design": test_condition_design.validate,
    "test-case-design": test_case_design.validate,
    "coverage-analysis": coverage_analysis.validate,
    "adversarial-review": adversarial_review.validate,
}
