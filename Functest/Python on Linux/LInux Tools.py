import subprocess

# 执行简单命令
result = subprocess.run(['ls'], capture_output=True, text=True)

print("返回码:", result.returncode)  # 0 表示成功
print("标准输出:\n", result.stdout)
print("标准错误:", result.stderr)