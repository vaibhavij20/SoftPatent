# Sample code for refactor suggestion testing
def inefficient_sum(numbers):
    result = 0
    for i in range(len(numbers)):
        result = result + numbers[i]
    return result

def main():
    nums = [1, 2, 3, 4, 5]
    print("Sum:", inefficient_sum(nums))

if __name__ == "__main__":
    main()
import unittest
from main import add, multiply

class TestMath(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
    def test_multiply(self):
        self.assertEqual(multiply(2, 3), 6)

if __name__ == "__main__":
    unittest.main()
