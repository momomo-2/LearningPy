x = input()

ls = x.split(',') + [' ']

head = 0
n = len(ls) - 1
tail = n
for i in range(n - 1):
    t = ls[head]
    head = (head + 1) % n
    for j in range(n - 1):
        if t < ls[head]:
            ls[tail] = t
            t = ls[head]
        else:
            ls[tail] = ls[head]
        head = (head + 1) % n
        tail = (tail + 1) % n
    ls[tail] = t
    tail = (tail + 1) % n

for i in range(n - 1):
    print(ls[head], end=',')
    head = (head + 1) % n
print(ls[head])
