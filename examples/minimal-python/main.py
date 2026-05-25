"""A tiny CLI that prints a greeting."""


def main() -> None:
    name = input("Your name: ").strip() or "stranger"
    print(f"Hello, {name}.")


if __name__ == "__main__":
    main()
