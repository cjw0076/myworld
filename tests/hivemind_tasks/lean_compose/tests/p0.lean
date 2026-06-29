-- Leaf p0 oracle reference.
-- lean_oracle uses this file's name (p0.lean) to locate the model's generated file
-- in artifact_dir and runs lean on it. A valid proof of any theorem in that file
-- yields exit 0; a type error or syntax error yields exit nonzero.
--
-- Reference solution (also used to verify the oracle is wired correctly):
theorem p0 : (0 : Nat) + 0 = 2 * 0 := by decide
