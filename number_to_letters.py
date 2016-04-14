from __future__ import print_function


def generate_letters(number_from_input):
    number = int(number_from_input)
    if number < 1:
        raise Exception("Input number needs to be greater than one")
    numbers_list = []
    _number = number
    while _number != 0:
        quotient, remainder = divmod(_number, 26)
        _number = quotient
        if quotient == 0 and remainder < 25:
            number_to_insert = remainder - 1
        else:
            number_to_insert = remainder
        numbers_list.insert(0, number_to_insert)
    letter_list = []
    for letter_number in numbers_list:
        letter = chr(ord('A') + letter_number)
        letter_list.append(letter)
    final_string = "".join(letter_list)
    return final_string

if __name__ == "__main__":
    number_is_good = False
    input_number = 0
    while not number_is_good:
        input_number = input("Input number to convert into letters: ")
        try:
            input_number = int(input_number)
            if input_number < 0:
                print("Input number needs to be a positive integer")
            else:
                number_is_good = True
        except ValueError:
            print("Input was not an integer")
    output = generate_letters(input_number)
    print("Letter Sequence is:", output)
