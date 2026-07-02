from solution import ipv4_lenient
def test_a(): assert ipv4_lenient("01.1.1.1") is True
def test_b(): assert ipv4_lenient("192.168.001.1") is True
def test_c(): assert ipv4_lenient("256.1.1.1") is False
def test_d(): assert ipv4_lenient("1.1.1") is False
def test_e(): assert ipv4_lenient("1.2.3.a") is False
