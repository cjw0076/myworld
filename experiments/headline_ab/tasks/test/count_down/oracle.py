from solution import count_down
def test_a(): assert count_down(5,1)==[5,4,3,2,1]
def test_b(): assert count_down(3,3)==[3]
def test_c(): assert count_down(1,5)==[]
def test_d(): assert count_down(0,-2)==[0,-1,-2]
