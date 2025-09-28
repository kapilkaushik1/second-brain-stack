# Python Programming Guide

Python is a high-level, interpreted programming language known for its simplicity, readability, and versatility. Created by Guido van Rossum and first released in 1991, Python has become one of the most popular programming languages in the world.

## Why Python?

### Readability and Simplicity
Python's syntax is designed to be intuitive and closely resembles natural language, making it easy for beginners to learn and for experienced developers to read and maintain.

```python
# Python code is clean and readable
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

numbers = [calculate_fibonacci(i) for i in range(10)]
print("First 10 Fibonacci numbers:", numbers)
```

### Versatility
Python can be used for:
- Web development (Django, Flask, FastAPI)
- Data science and machine learning (pandas, NumPy, scikit-learn)
- Automation and scripting
- Desktop applications (Tkinter, PyQt)
- Game development (Pygame)
- Scientific computing (SciPy, matplotlib)

## Core Concepts

### Variables and Data Types
Python is dynamically typed, meaning you don't need to explicitly declare variable types.

```python
# Different data types
name = "Alice"           # String
age = 30                 # Integer
height = 5.6            # Float
is_student = False      # Boolean
hobbies = ["reading", "coding", "hiking"]  # List
person = {"name": "Alice", "age": 30}      # Dictionary
```

### Control Structures

#### Conditional Statements
```python
score = 85

if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
else:
    grade = "F"

print(f"Your grade is: {grade}")
```

#### Loops
```python
# For loop
fruits = ["apple", "banana", "orange"]
for fruit in fruits:
    print(f"I like {fruit}")

# While loop
count = 0
while count < 5:
    print(f"Count: {count}")
    count += 1
```

### Functions
Functions are reusable blocks of code that perform specific tasks.

```python
def greet(name, greeting="Hello"):
    """
    Greet a person with a custom message.
    
    Args:
        name (str): The person's name
        greeting (str): The greeting message (default: "Hello")
    
    Returns:
        str: The formatted greeting
    """
    return f"{greeting}, {name}!"

# Function calls
print(greet("Alice"))
print(greet("Bob", "Hi"))
```

### Object-Oriented Programming

```python
class Vehicle:
    def __init__(self, make, model, year):
        self.make = make
        self.model = model
        self.year = year
        self.is_running = False
    
    def start(self):
        self.is_running = True
        print(f"{self.make} {self.model} is now running")
    
    def stop(self):
        self.is_running = False
        print(f"{self.make} {self.model} has stopped")

class Car(Vehicle):
    def __init__(self, make, model, year, doors):
        super().__init__(make, model, year)
        self.doors = doors
    
    def honk(self):
        print("Beep beep!")

# Creating objects
my_car = Car("Toyota", "Camry", 2022, 4)
my_car.start()
my_car.honk()
```

## Advanced Features

### List Comprehensions
Concise way to create lists based on existing lists.

```python
# Traditional approach
squares = []
for x in range(10):
    squares.append(x**2)

# List comprehension
squares = [x**2 for x in range(10)]

# With condition
even_squares = [x**2 for x in range(10) if x % 2 == 0]
```

### Lambda Functions
Short, anonymous functions for simple operations.

```python
# Lambda function
square = lambda x: x**2
print(square(5))  # Output: 25

# Using with built-in functions
numbers = [1, 2, 3, 4, 5]
squared_numbers = list(map(lambda x: x**2, numbers))
even_numbers = list(filter(lambda x: x % 2 == 0, numbers))
```

### Exception Handling
Handle errors gracefully in your programs.

```python
def divide_numbers(a, b):
    try:
        result = a / b
        return result
    except ZeroDivisionError:
        print("Error: Cannot divide by zero")
        return None
    except TypeError:
        print("Error: Invalid input types")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
    finally:
        print("Division operation attempted")

# Usage
print(divide_numbers(10, 2))  # Output: 5.0
print(divide_numbers(10, 0))  # Error message
```

## Libraries and Frameworks

### Data Science
- **NumPy**: Numerical computing with arrays
- **pandas**: Data manipulation and analysis
- **matplotlib/seaborn**: Data visualization
- **scikit-learn**: Machine learning
- **Jupyter**: Interactive computing notebooks

### Web Development
- **Django**: Full-featured web framework
- **Flask**: Lightweight web framework
- **FastAPI**: Modern, fast web framework for APIs
- **Requests**: HTTP library for API consumption

### Automation and Scripting
- **os/sys**: System interaction
- **pathlib**: File system path handling
- **subprocess**: Running external commands
- **schedule**: Job scheduling
- **BeautifulSoup**: Web scraping

## Best Practices

### Code Style
Follow PEP 8 (Python Enhancement Proposal 8) for consistent code formatting:
- Use 4 spaces for indentation
- Limit lines to 79 characters
- Use descriptive variable names
- Add docstrings to functions and classes

### Virtual Environments
Use virtual environments to manage project dependencies:

```bash
# Create virtual environment
python -m venv myenv

# Activate (Linux/Mac)
source myenv/bin/activate

# Activate (Windows)
myenv\Scripts\activate

# Install packages
pip install requests numpy pandas

# Save dependencies
pip freeze > requirements.txt
```

### Error Handling
- Always handle potential errors appropriately
- Use specific exception types when possible
- Provide meaningful error messages
- Log errors for debugging purposes

### Testing
Write tests to ensure code reliability:

```python
import unittest

class TestMathOperations(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(2 + 2, 4)
    
    def test_division(self):
        self.assertEqual(10 / 2, 5)
    
    def test_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            10 / 0

if __name__ == '__main__':
    unittest.main()
```

## Getting Started

To begin programming in Python:

1. **Install Python** from python.org
2. **Choose an IDE** (VS Code, PyCharm, or Jupyter)
3. **Practice basic syntax** with simple programs
4. **Work on projects** that interest you
5. **Join the community** (Python forums, Discord, Reddit)
6. **Read documentation** and explore the standard library

Python's philosophy, summarized in "The Zen of Python," emphasizes:
- Beautiful is better than ugly
- Explicit is better than implicit
- Simple is better than complex
- Readability counts
- There should be one obvious way to do it

This makes Python an excellent choice for both beginners and experienced developers working on a wide range of applications.