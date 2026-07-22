from __future__ import annotations

import pytest

from calculator import add, divide, multiply, subtract
from calculator.__main__ import run


class TestAdd:
    def test_positive(self) -> None:
        assert add(2, 3) == 5

    def test_negative(self) -> None:
        assert add(-1, -2) == -3

    def test_float(self) -> None:
        assert add(1.5, 2.5) == 4.0


class TestSubtract:
    def test_basic(self) -> None:
        assert subtract(10, 3) == 7

    def test_negative_result(self) -> None:
        assert subtract(3, 10) == -7

    def test_float(self) -> None:
        assert subtract(5.5, 2.2) == pytest.approx(3.3)


class TestMultiply:
    def test_positive(self) -> None:
        assert multiply(4, 5) == 20

    def test_by_zero(self) -> None:
        assert multiply(7, 0) == 0

    def test_float(self) -> None:
        assert multiply(2.5, 4) == 10.0


class TestDivide:
    def test_exact(self) -> None:
        assert divide(10, 2) == 5

    def test_float_result(self) -> None:
        assert divide(7, 2) == 3.5

    def test_negative(self) -> None:
        assert divide(-6, 3) == -2


class TestDivideByZero:
    def test_raises(self) -> None:
        with pytest.raises(ZeroDivisionError, match="divisão por zero"):
            divide(5, 0)

    def test_raises_zero_zero(self) -> None:
        with pytest.raises(ZeroDivisionError):
            divide(0, 0)

    def test_raises_negative_zero(self) -> None:
        with pytest.raises(ZeroDivisionError):
            divide(-3, 0)


class TestTerminalCalculator:
    def test_performs_addition_and_exits(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        inputs = iter(("1", "10", "5", "0"))
        monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

        run()

        output = capsys.readouterr().out
        assert "Adição: 10.0 + 5.0 = 15.0" in output
        assert "Encerrando calculadora." in output

    def test_exits_cleanly_on_end_of_input(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def end_input(_prompt: str) -> str:
            raise EOFError

        monkeypatch.setattr("builtins.input", end_input)

        run()

        assert "Entrada encerrada." in capsys.readouterr().out
