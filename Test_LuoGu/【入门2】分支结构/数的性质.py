x = int(input())
if x % 2 == 0:
    if x > 4 and x<= 12:
        print(1,1,0,0)
    else:
        print(0,1,1,0)
else:
    if x > 4 and x <= 12:
        print(0,1,1,0)
    else:
        print(0,0,0,1)