"""Programming concepts the chatbot teaches (proposal Section 3.1, Table 3.1).

The first three are enabled for the FYP1 prototype. ``focus`` tells the
model what diagnostic questions 2 and 3 should ask about (question 1 is
always about general programming experience).
"""

CONCEPTS = {
    "variables": {
        "title": "Variables and Data Types",
        "subtopics": "integers, floats, strings, booleans, type conversion",
        "enabled": True,
        "focus": [
            "Ask what they think a variable is, in their own words.",
            "Ask a tiny question about data types, for example what type a value like 3.5 or \"hello\" is.",
        ],
    },
    "operators": {
        "title": "Operators",
        "subtopics": "arithmetic, comparison, logical operators",
        "enabled": True,
        "focus": [
            "Ask them to predict the result of a small arithmetic expression that uses / or %, such as 7 / 2.",
            "Ask a tiny question about comparison or logical operators, for example what 5 > 3 and 2 > 4 gives.",
        ],
    },
    "control_flow": {
        "title": "Control Flow",
        "subtopics": "if/else statements, for loops, while loops",
        "enabled": True,
        "focus": [
            "Ask what they think an if statement does, in their own words.",
            "Ask a tiny question about loops, for example how many times a for loop over range(3) runs.",
        ],
    },
    "functions": {"title": "Functions and Scope", "subtopics": "parameters, return values, local vs. global scope", "enabled": False, "focus": []},
    "oop": {"title": "Object-Oriented Programming Basics", "subtopics": "classes, objects, attributes, methods", "enabled": False, "focus": []},
    "data_structures": {"title": "Introductory Data Structures", "subtopics": "lists, indexing, iteration", "enabled": False, "focus": []},
}
