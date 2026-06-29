-- Reference solution: leaf p0 (exit 0)
-- Verify: PATH="$HOME/.elan/bin:$PATH" lean solution/p0.lean
theorem p0 : (0 : Nat) + 0 = 2 * 0 := by decide
