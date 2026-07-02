from solution import fizzbuzz_swapped
def test_a(): assert fizzbuzz_swapped(5)==["1","2","Buzz","4","Fizz"]
def test_b(): assert fizzbuzz_swapped(3)==["1","2","Buzz"]
def test_c(): assert fizzbuzz_swapped(15)[-1]=="FizzBuzz"
def test_d(): assert fizzbuzz_swapped(1)==["1"]
