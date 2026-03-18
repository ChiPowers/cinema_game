from config import DIFFICULTY_HOPS, MIN_ACTOR_POPULARITY


class TestDifficultyHops:
    def test_all_levels_present(self):
        assert set(DIFFICULTY_HOPS.keys()) == {"easy", "medium", "hard"}

    def test_values_are_tuples_of_two_ints(self):
        for level, (lo, hi) in DIFFICULTY_HOPS.items():
            assert isinstance(lo, int), f"{level} low bound is not int"
            assert isinstance(hi, int), f"{level} high bound is not int"

    def test_low_bound_le_high_bound(self):
        for level, (lo, hi) in DIFFICULTY_HOPS.items():
            assert lo <= hi, f"{level}: {lo} > {hi}"

    def test_difficulty_ordering(self):
        assert DIFFICULTY_HOPS["easy"][1] < DIFFICULTY_HOPS["medium"][1]
        assert DIFFICULTY_HOPS["medium"][1] < DIFFICULTY_HOPS["hard"][1]


class TestMinActorPopularity:
    def test_all_levels_present(self):
        assert set(MIN_ACTOR_POPULARITY.keys()) == {"easy", "medium", "hard"}

    def test_values_are_positive(self):
        for level, pop in MIN_ACTOR_POPULARITY.items():
            assert pop > 0, f"{level} popularity is not positive"

    def test_easy_has_highest_floor(self):
        assert MIN_ACTOR_POPULARITY["easy"] > MIN_ACTOR_POPULARITY["medium"]
        assert MIN_ACTOR_POPULARITY["medium"] > MIN_ACTOR_POPULARITY["hard"]
