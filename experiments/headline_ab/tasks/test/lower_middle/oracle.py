from solution import lower_middle
def test_a(): assert lower_middle([1,2,3,4])==2
def test_b(): assert lower_middle([1,2,3])==2
def test_c(): assert lower_middle([])is None
def test_d(): assert lower_middle([10,20,30,40,50,60])==30
