def greet(name):
    return "hello "+name

greet_someone = greet
greet_someone("John")

def greet(name):
    def get_message():
        return "Hello "

    result = get_message()+name
    return result

greet("John")

# Outputs: Hello John
