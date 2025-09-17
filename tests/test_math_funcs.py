import pytest
from math_funcs import add, sub, divide

def test_add_basic():
    assert add(2, 3) == 5

def test_sub_basic():
    assert sub(5, 2) == 3

def test_divide_success():
    assert divide(6, 2) == 3

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)

