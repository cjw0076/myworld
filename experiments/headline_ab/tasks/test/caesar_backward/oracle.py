from solution import caesar_backward
def test_a(): assert caesar_backward("bcd",1)=="abc"
def test_b(): assert caesar_backward("abc",1)=="zab"
def test_c(): assert caesar_backward("Mjqqt, Btwqi!",5)=="Hello, World!"
def test_d(): assert caesar_backward("abc",0)=="abc"
