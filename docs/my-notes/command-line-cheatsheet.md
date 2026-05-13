# 命令行常用指令速查表

本文以常见 Shell 命令为主，适用于 Linux、macOS、Git Bash、WSL 等环境；Windows PowerShell 对应命令单独列出。

## 1. 查看当前位置与目录内容

```bash
pwd
ls
ls -l
ls -a
ls -lh
ls -la
```

PowerShell：

```powershell
Get-Location
Get-ChildItem
Get-ChildItem -Force
```

## 2. 切换目录

```bash
cd <目录>
cd ..
cd ../..
cd ~
cd -
```

PowerShell：

```powershell
Set-Location <目录>
Set-Location ..
```

## 3. 创建文件和目录

```bash
mkdir <目录名>
mkdir -p <多级目录>
touch <文件名>
```

PowerShell：

```powershell
New-Item -ItemType Directory <目录名>
New-Item -ItemType File <文件名>
```

## 4. 复制、移动、删除

```bash
cp <源文件> <目标文件>
cp -r <源目录> <目标目录>
mv <源路径> <目标路径>
rm <文件名>
rm -r <目录名>
rm -rf <目录名>
```

PowerShell：

```powershell
Copy-Item <源路径> <目标路径>
Copy-Item <源目录> <目标目录> -Recurse
Move-Item <源路径> <目标路径>
Remove-Item <文件名>
Remove-Item <目录名> -Recurse
```

提示：删除命令要谨慎，尤其是 `rm -rf` 和 `Remove-Item -Recurse`。

## 5. 查看文件内容

```bash
cat <文件名>
less <文件名>
head <文件名>
head -n 20 <文件名>
tail <文件名>
tail -n 20 <文件名>
tail -f <日志文件>
```

PowerShell：

```powershell
Get-Content <文件名>
Get-Content <文件名> -TotalCount 20
Get-Content <文件名> -Tail 20
Get-Content <日志文件> -Wait
```

## 6. 搜索文件和内容

```bash
find . -name "*.js"
find . -type f -name "*.md"
grep "关键词" <文件名>
grep -r "关键词" .
grep -rn "关键词" .
```

更推荐使用 `rg`：

```bash
rg "关键词"
rg "关键词" .
rg --files
rg --files | rg "\.md$"
```

PowerShell：

```powershell
Get-ChildItem -Recurse -Filter *.js
Select-String -Path <文件名> -Pattern "关键词"
Get-ChildItem -Recurse | Select-String -Pattern "关键词"
```

## 7. 压缩与解压

```bash
tar -czf archive.tar.gz <目录或文件>
tar -xzf archive.tar.gz
zip -r archive.zip <目录或文件>
unzip archive.zip
```

PowerShell：

```powershell
Compress-Archive -Path <目录或文件> -DestinationPath archive.zip
Expand-Archive -Path archive.zip -DestinationPath <目标目录>
```

## 8. 查看进程与端口

```bash
ps aux
ps aux | grep <关键词>
top
kill <pid>
kill -9 <pid>
lsof -i :<端口号>
```

Windows / PowerShell：

```powershell
Get-Process
Get-Process | Where-Object { $_.ProcessName -like "*关键词*" }
Stop-Process -Id <pid>
netstat -ano | findstr :<端口号>
```

## 9. 网络请求与下载

```bash
curl <URL>
curl -I <URL>
curl -L <URL>
curl -o <文件名> <URL>
wget <URL>
```

PowerShell：

```powershell
Invoke-WebRequest <URL>
Invoke-WebRequest <URL> -OutFile <文件名>
```

## 10. 环境变量

```bash
echo $PATH
export NAME=value
unset NAME
env
```

PowerShell：

```powershell
$env:PATH
$env:NAME = "value"
Remove-Item Env:NAME
Get-ChildItem Env:
```

## 11. 权限相关

```bash
chmod +x <文件名>
chmod 755 <文件名>
chown <用户>:<用户组> <文件名>
sudo <命令>
```

说明：

- `chmod +x` 给脚本增加可执行权限。
- `sudo` 用管理员权限执行命令。

## 12. 命令组合

```bash
命令1 && 命令2
命令1 || 命令2
命令1 | 命令2
命令 > output.txt
命令 >> output.txt
命令 2> error.txt
```

说明：

- `&&` 前一个命令成功后执行下一个。
- `||` 前一个命令失败后执行下一个。
- `|` 把前一个命令的输出传给后一个命令。
- `>` 覆盖写入文件。
- `>>` 追加写入文件。

## 13. 常用开发命令

```bash
node -v
npm -v
npm install
npm run dev
npm run build
npm test
python --version
python -m venv .venv
pip install -r requirements.txt
```

PowerShell 激活 Python 虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

## 14. 实用小技巧

```bash
history
clear
which <命令>
whereis <命令>
date
whoami
echo "hello"
```

PowerShell：

```powershell
Get-History
Clear-Host
Get-Command <命令>
Get-Date
whoami
Write-Output "hello"
```

## 15. 常见路径写法

```text
.        当前目录
..       上一级目录
~        用户主目录
/        Linux/macOS 根目录
C:\      Windows C 盘根目录
```

