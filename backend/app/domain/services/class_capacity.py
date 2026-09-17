class ClassCapacityChecker:
    @staticmethod
    def can_assign(current_count: int, capacity: int) -> bool:
        return current_count < capacity

    @staticmethod
    def occupancy_rate(current_count: int, capacity: int) -> float:
        if capacity <= 0:
            return 0.0
        return round((current_count / capacity) * 100, 2)

    @staticmethod
    def validate_assignment(current_count: int, capacity: int) -> None:
        if not ClassCapacityChecker.can_assign(current_count, capacity):
            raise ValueError("Sınıf kontenjanı dolu")
