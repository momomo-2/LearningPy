n1 = int(input())
n2 = int(input())
shu = []

for i in range(1, max(n1, n2)):
    if n1 % i == 0 and n2 % i == 0:
        shu.append(i)

print(shu)