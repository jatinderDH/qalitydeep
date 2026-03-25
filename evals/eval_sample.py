"""Sample Python-based evaluation definitions."""
from qalitydeep import eval_suite, eval_case


@eval_suite(metrics=["code_syntax", "exact_match"], threshold=0.8)
def test_basic_functions():
    """Test basic Python function generation."""
    return [
        eval_case(
            input="Write a function that adds two numbers",
            expected_output="""def add(a, b):
    return a + b""",
        ),
        eval_case(
            input="Write a function that checks if a number is even",
            expected_output="""def is_even(n):
    return n % 2 == 0""",
        ),
    ]
