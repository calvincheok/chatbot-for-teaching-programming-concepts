/* Programming concepts the chatbot teaches (proposal Section 3.1, Table 3.1).
   Only the first is enabled for the FYP1 prototype. */
"use strict";
var PyTutor = window.PyTutor || (window.PyTutor = {});

PyTutor.CONCEPTS = {
  variables: { title: "Variables and Data Types", subtopics: "integers, floats, strings, booleans, type conversion", enabled: true },
  operators: { title: "Operators", subtopics: "arithmetic, comparison, logical operators", enabled: false },
  control_flow: { title: "Control Flow", subtopics: "if/else statements, for loops, while loops", enabled: false },
  functions: { title: "Functions and Scope", subtopics: "parameters, return values, local vs. global scope", enabled: false },
  oop: { title: "Object-Oriented Programming Basics", subtopics: "classes, objects, attributes, methods", enabled: false },
  data_structures: { title: "Introductory Data Structures", subtopics: "lists, indexing, iteration", enabled: false },
};
