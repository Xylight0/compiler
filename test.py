# arr2 = [True, False, True]

# arr1 = [0, 4, 6, 7]

# arr = 5 * [8]

# print(arr2[1])

# print(arr[2])

# arr[4] = 6

# print(arr[4])

# print(arr[3])

# print(arr1[1])

# print(len(arr))

# arr3 = [[3, 4], [5, 6]]

# print(arr3[0][1])

# arr = 8179 * [0]
# print(len(arr))

# We have 65536 bytes of mem
# So we have 65536 - 100 - 4 bytes available.
# This is enough for exactly 16358 elements

# arr_bool = 16358 * [True]
# print(len(arr_bool))

### run error
# We have max 65536 bytes of memory, 100 bytes for data

# arr_bool = 16359 * [True]
# print(len(arr_bool))

### run error
n = 10001  # needs 80012 bytes of memory
arr = n * [0]
arr[0] = 42
arr[n - 2] = 10
arr[n - 1] = 11

print(arr[0])
print(arr[1])
print(arr[n - 3])
print(arr[n - 2])
print(arr[n - 1])
