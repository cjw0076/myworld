from solution import roman_additive
def test_a(): assert roman_additive("III")==3
def test_b(): assert roman_additive("IIII")==4
def test_c(): assert roman_additive("IV")==6
def test_d(): assert roman_additive("XIIII")==14
def test_e(): assert roman_additive("VI")==6
