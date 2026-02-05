#import random
#x = random. randint(6, 50)
x = int(input())
print('在链表data中插入一个值为%d的数' % x)
data = [[14, 1], [26, 4], [5, 0], [49, -1], [37, 3]]
head = 2
q = head
while q != -1:
    if x > data[q][0]:
        p = q
        q = data[q][1]
    else:
        break
data.append([x, q])
data[p][1] = len(data) - 1
q = head
while q != -1:
    print(data[q][0], end='->')
    q = data[q][1]
