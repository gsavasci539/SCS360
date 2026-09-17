from decimal import Decimal, ROUND_HALF_UP


class Money:
    def __init__(self, amount: Decimal | str | float | int):
        if isinstance(amount, float):
            raise ValueError("Float kullanılamaz, Decimal kullanın")
        self.amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __str__(self) -> str:
        return f"{self.amount:.2f}"

    def __add__(self, other: "Money") -> "Money":
        return Money(self.amount + other.amount)

    def __sub__(self, other: "Money") -> "Money":
        return Money(self.amount - other.amount)

    def __gt__(self, other: "Money") -> bool:
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        return self.amount >= other.amount

    def __lt__(self, other: "Money") -> bool:
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        return self.amount <= other.amount
