from solution import keep_every_third
def test_a(): assert keep_every_third([10,11,12,13,14,15,16])==[10,13,16]
def test_b(): assert keep_every_third([])==[]
def test_c(): assert keep_every_third([1,2])==[1]
def test_d(): assert keep_every_third([0,1,2,3,4,5])==[0,3]
