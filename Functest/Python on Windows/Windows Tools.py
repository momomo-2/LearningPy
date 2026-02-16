import subprocess

def run_windows_tool(command, shell=False):
    """
    运行 Windows 工具并获取输出
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='gbk',
            errors='ignore',
            shell=shell  # True 时通过系统 shell 执行
        )
        return {
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# 示例1: 获取系统信息（systeminfo）
print("=== 系统信息 ===")
info = run_windows_tool(['systeminfo'], shell=True)
print(info['stdout'][:500] if info['success'] else info['stderr'])

# 示例2: 获取 IP 配置
print("\n=== IP 配置 ===")
ipconfig = run_windows_tool(['ipconfig', '/all'])
print(ipconfig['stdout'][:800])

# 示例3: 获取任务列表
print("\n=== 任务列表（前5个） ===")
tasks = run_windows_tool(['tasklist'])
lines = tasks['stdout'].split('\n')[:7]
print('\n'.join(lines))

# 示例4: 获取磁盘空间
print("\n=== 磁盘空间 ===")
disk = run_windows_tool(['wmic', 'logicaldisk', 'get', 'size,freespace,caption'])
print(disk['stdout'])