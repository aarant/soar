import os

for i in os.listdir(os.path.join('.', 'source/')):
    i = os.path.join('source/', i)
    if os.path.isfile(i) and os.path.splitext(i)[1] == '.rst':
        if os.path.splitext(i)[0] != 'index':
            with open(i, 'r') as f:
                text = f.read()
                end = text.find('\n')
                for word in [' module', ' package']:
                    index = text.find(word, 0, end)
                    if index != -1:
                        a = text[:index]
                        b = text[index+len(word):]
                        text = a + b
                        break
            with open(i, 'w') as f:
                f.write(text)
            print(i)
