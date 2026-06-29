-- Reference solution: direct proof of T (exit 0)
-- ARM A can solve this in one shot with omega; ARM B cannot compose p0+p1 into T.
-- This demonstrates the structural composition gap is not a model-capability issue:
-- T is provable directly, but NOT derivable from the two finite instances alone.
theorem t : ∀ n : Nat, n + n = 2 * n := by intro n; omega
