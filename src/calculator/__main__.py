from __future__ import annotations

from calculator import add, divide, multiply, subtract

OPERATIONS = {
    "1": ("Adição", add),
    "2": ("Subtração", subtract),
    "3": ("Multiplicação", multiply),
    "4": ("Divisão", divide),
}


def build_menu() -> str:
    lines = ["=== Calculadora ===\n", "Escolha a operação:\n"]
    for key, (name, _) in OPERATIONS.items():
        lines.append(f"  {key} - {name}\n")
    lines.append("  0 - Sair\n")
    return "".join(lines)


def read_choice() -> str:
    return input("Opção: ").strip()


def read_number(prompt: str) -> float:
    while True:
        raw = input(prompt).strip()
        try:
            return float(raw)
        except ValueError:
            print(f"'{raw}' não é um número válido. Tente novamente.")


def run() -> None:
    print(build_menu())
    operation_symbols = {"1": "+", "2": "-", "3": "*", "4": "/"}

    while True:
        try:
            choice = read_choice()
        except EOFError:
            print("\nEntrada encerrada.")
            return

        if choice == "0":
            print("Encerrando calculadora.")
            return

        if choice not in OPERATIONS:
            print("Opção inválida. Escolha uma opção de 0 a 4.")
            continue

        op_name, op_func = OPERATIONS[choice]

        try:
            a = read_number("Primeiro valor: ")
            b = read_number("Segundo valor: ")
        except EOFError:
            print("\nEntrada encerrada.")
            return

        try:
            result = op_func(a, b)
            print(f"{op_name}: {a} {operation_symbols[choice]} {b} = {result}")
        except ZeroDivisionError as error:
            print(f"Erro: {error}")

        print()


if __name__ == "__main__":
    run()
