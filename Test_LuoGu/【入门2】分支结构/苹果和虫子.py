m, t, s = map(int, input().split())
if t == 0:
    print(0)
else:
    total_time = m * t
    if s >= total_time:
        print(0)
    else:
        remaining_time = total_time - s
        print((remaining_time + t - 1) // t)
