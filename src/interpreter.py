class Interpreter:
    def __init__(self):
        self.stack = []

    def load_value(self, number):
        self.stack.append(number)

    def print_answer(self):
        answer = self.stack.pop()
        print(answer)

    def add_two_values(self):
        first_number = self.stack.pop()
        second_number = self.stack.pop()
        total = first_number + second_number
        self.stack.append(total)

    def run_code(self, what_to_run):
        instructions = what_to_run["instructions"]
        numbers = what_to_run["numbers"]

        for each_step in instructions:
            instruction, argument = each_step
            if instruction == "LOAD_VALUE":
                number = numbers[argument]
                self.load_value(number)
            elif instruction == "ADD_TWO_VALUES":
                self.add_two_values()
            elif instruction == "PRINT_ANSWER":
                self.print_answer()
